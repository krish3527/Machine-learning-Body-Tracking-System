"""
core/yoga_analyzer.py
Rule-based Yoga Pose posture alignment evaluator and hold timer.
Supports 4 essential poses:
1. Tadasana (Mountain Pose)
2. Tree Pose (Vrikshasana)
3. Warrior II (Virabhadrasana II)
4. Downward Dog (Adho Mukha Svanasana)
Uses MediaPipe landmarks and joint angles to evaluate posture, provide instant cues,
and track hold durations.
"""

import time
from typing import Dict, Any, List, Optional
import numpy as np

# Import angle_utils
import os, sys
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, ".."))
_REPO_SRC = os.path.join(_PROJECT_ROOT, "Doomsday-Sports-ML-REPO", "src")
_FALLBACK_SRC = os.path.join(_PROJECT_ROOT, "src")
for src_path in [_REPO_SRC, _FALLBACK_SRC]:
    if os.path.exists(src_path) and src_path not in sys.path:
        sys.path.insert(0, src_path)

try:
    from angle_utils import calculate_angle
except ImportError:
    def calculate_angle(a, b, c):
        BA = np.array(a) - np.array(b)
        BC = np.array(c) - np.array(b)
        dot = np.dot(BA, BC)
        mag = np.linalg.norm(BA) * np.linalg.norm(BC)
        if mag == 0:
            return 0.0
        cos_angle = np.clip(dot / mag, -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_angle)))


YOGA_POSES_METADATA = {
    "tadasana": {
        "name": "Tadasana",
        "sanskrit": "Mountain Pose",
        "description": "Standing tall with upright spine, arms relaxed alongside or extended, chest open, weight evenly balanced.",
        "target_hold_default": 10,
        "key_focus": "Spine elongation and level shoulders"
    },
    "tree": {
        "name": "Tree Pose",
        "sanskrit": "Vrikshasana",
        "description": "Standing strong on one leg while placing the sole of the opposite foot onto the inner thigh or calf.",
        "target_hold_default": 10,
        "key_focus": "Single leg balance and knee outward opening"
    },
    "warrior2": {
        "name": "Warrior II",
        "sanskrit": "Virabhadrasana II",
        "description": "Wide stance with front knee bent at 90°, back leg straight, and both arms extended horizontally parallel to floor.",
        "target_hold_default": 10,
        "key_focus": "Front knee depth and horizontal arm extension"
    },
    "downward_dog": {
        "name": "Downward Dog",
        "sanskrit": "Adho Mukha Svanasana",
        "description": "Inverted 'V' shape with hands and feet pressing into the floor, hips pushed up and back, arms straight.",
        "target_hold_default": 10,
        "key_focus": "Hip height and elongated spine"
    }
}


class YogaAnalyzer:
    def __init__(self, selected_pose: str = "tadasana", target_hold_seconds: int = 10):
        self.selected_pose = selected_pose.lower()
        self.target_hold_seconds = target_hold_seconds
        
        # Hold state
        self.is_holding: bool = False
        self.hold_start_time: Optional[float] = None
        self.current_hold_duration: float = 0.0
        self.best_hold_duration: float = 0.0
        self.hold_completed: bool = False
        
        # Audio / TTS state
        self.last_tts_message: Optional[str] = None
        self.last_tts_time: float = 0.0
        self.tts_cooldown: float = 3.5

    def reset(self):
        self.is_holding = False
        self.hold_start_time = None
        self.current_hold_duration = 0.0
        self.best_hold_duration = 0.0
        self.hold_completed = False
        self.last_tts_message = None
        self.last_tts_time = 0.0

    def set_pose(self, pose_name: str):
        if self.selected_pose != pose_name.lower():
            self.selected_pose = pose_name.lower()
            self.reset()

    def analyze(self, landmarks_dict: dict, metrics: dict) -> dict:
        """
        Evaluates user's posture against the selected yoga pose criteria.
        Returns accuracy, status, feedback messages, hold timer, and visual guidance cues.
        """
        if not landmarks_dict or not metrics:
            return {
                "pose": self.selected_pose,
                "pose_name": YOGA_POSES_METADATA.get(self.selected_pose, {}).get("name", "Yoga"),
                "status": "WAITING",
                "accuracy": 0,
                "feedback": ["Stand where your full body is visible in the frame."],
                "is_holding": False,
                "hold_duration": 0.0,
                "target_hold": self.target_hold_seconds,
                "hold_completed": False,
                "tts_prompt": None,
                "animated_cue": None
            }

        # Check pose-specific rules
        pose_key = self.selected_pose
        if pose_key == "tadasana":
            eval_result = self._eval_tadasana(landmarks_dict, metrics)
        elif pose_key == "tree":
            eval_result = self._eval_tree_pose(landmarks_dict, metrics)
        elif pose_key == "warrior2":
            eval_result = self._eval_warrior2(landmarks_dict, metrics)
        elif pose_key == "downward_dog":
            eval_result = self._eval_downward_dog(landmarks_dict, metrics)
        else:
            eval_result = self._eval_tadasana(landmarks_dict, metrics)

        # Update Hold Timer
        now = time.time()
        is_aligned = eval_result["is_aligned"]

        if is_aligned:
            if not self.is_holding:
                self.is_holding = True
                self.hold_start_time = now
            self.current_hold_duration = now - self.hold_start_time
            if self.current_hold_duration > self.best_hold_duration:
                self.best_hold_duration = self.current_hold_duration

            if self.current_hold_duration >= self.target_hold_seconds:
                self.hold_completed = True
        else:
            self.is_holding = False
            self.hold_start_time = None
            self.current_hold_duration = 0.0

        # Status text
        if self.hold_completed:
            status = "POSE COMPLETED ✓"
            eval_result["feedback"].insert(0, f"Completed {self.target_hold_seconds}s hold! Great posture.")
        elif self.is_holding:
            remaining = max(0, int(self.target_hold_seconds - self.current_hold_duration))
            status = f"HOLDING ({remaining}s remaining)"
        elif is_aligned:
            status = "GOOD ALIGNMENT"
        else:
            status = "NEEDS ADJUSTMENT"

        # Handle TTS
        tts_candidate = eval_result.get("tts_candidate")
        if self.hold_completed and self.current_hold_duration - self.target_hold_seconds < 1.0:
            tts_candidate = "Target hold completed. Excellent job."

        tts_to_speak = None
        if tts_candidate and (now - self.last_tts_time > self.tts_cooldown):
            if tts_candidate != self.last_tts_message or (now - self.last_tts_time > self.tts_cooldown * 2):
                tts_to_speak = tts_candidate
                self.last_tts_message = tts_candidate
                self.last_tts_time = now

        return {
            "pose": self.selected_pose,
            "pose_name": YOGA_POSES_METADATA.get(self.selected_pose, {}).get("name", "Yoga"),
            "status": status,
            "accuracy": eval_result["accuracy"],
            "feedback": eval_result["feedback"][:2],
            "is_holding": self.is_holding,
            "hold_duration": round(self.current_hold_duration, 1),
            "best_hold_duration": round(self.best_hold_duration, 1),
            "target_hold": self.target_hold_seconds,
            "hold_completed": self.hold_completed,
            "tts_prompt": tts_to_speak,
            "animated_cue": eval_result.get("animated_cue")
        }

    def _eval_tadasana(self, lm: dict, metrics: dict) -> dict:
        """Tadasana: Stand tall, straight legs, vertical torso, shoulders level."""
        feedback = []
        cues = []
        score = 100

        l_knee = metrics["left"]["knee_angle"]
        r_knee = metrics["right"]["knee_angle"]
        torso_lean = metrics["torso_angle"]

        # Check leg extension (165° - 180°)
        if l_knee < 160 or r_knee < 160:
            score -= 30
            feedback.append("Straighten both knees fully.")
            cues.append("Straighten knees ↑")

        # Check torso uprightness (< 15° lean)
        if torso_lean > 15:
            score -= 30
            feedback.append("Stand straight and lengthen your spine.")
            cues.append("Straighten spine ↑")

        # Check shoulder level
        sh_diff = abs(lm[11]["y"] - lm[12]["y"])
        if sh_diff > 0.06:
            score -= 20
            feedback.append("Level your shoulders evenly.")

        is_aligned = score >= 75
        tts = "Hold this position." if is_aligned else (feedback[0] if feedback else None)
        animated_cue = {"type": "arrow_up", "direction": "up", "text": cues[0]} if cues else None

        if is_aligned and not feedback:
            feedback.append("Good alignment. Hold steady and breathe.")

        return {
            "is_aligned": is_aligned,
            "accuracy": max(0, score),
            "feedback": feedback,
            "tts_candidate": tts,
            "animated_cue": animated_cue
        }

    def _eval_tree_pose(self, lm: dict, metrics: dict) -> dict:
        """
        Tree Pose:
        One standing leg extended (~165-180°), one bent leg (< 110°),
        bent foot placed along inner leg, hands centered or raised.
        """
        feedback = []
        cues = []
        score = 100

        l_knee = metrics["left"]["knee_angle"]
        r_knee = metrics["right"]["knee_angle"]

        # Identify which leg is standing vs bent
        if l_knee > 155 and r_knee < 130:
            standing_knee = l_knee
            bent_knee = r_knee
            bent_side = "right"
        elif r_knee > 155 and l_knee < 130:
            standing_knee = r_knee
            bent_knee = l_knee
            bent_side = "left"
        else:
            # Neither clearly bent
            return {
                "is_aligned": False,
                "accuracy": 40,
                "feedback": ["Shift weight to one leg and lift the opposite foot onto your calf or thigh."],
                "tts_candidate": "Raise one foot into Tree Pose.",
                "animated_cue": {"type": "arrow_up", "direction": "up", "text": "Lift foot to leg ↑"}
            }

        # Standing leg check
        if standing_knee < 162:
            score -= 25
            feedback.append("Lock and straighten your standing leg.")
            cues.append("Straighten standing leg ↑")

        # Bent leg check (should be bent tight enough)
        if bent_knee > 120:
            score -= 25
            feedback.append(f"Bend your {bent_side} leg higher up the leg.")
            cues.append("Raise foot higher ↑")

        # Torso upright check
        if metrics["torso_angle"] > 18:
            score -= 20
            feedback.append("Keep your chest upright over your hips.")

        is_aligned = score >= 70
        tts = "Good balance, hold steady." if is_aligned else (feedback[0] if feedback else None)
        animated_cue = {"type": "arrow_up", "direction": "up", "text": cues[0]} if cues else None

        if is_aligned and not feedback:
            feedback.append("Excellent balance! Fix your gaze forward and hold.")

        return {
            "is_aligned": is_aligned,
            "accuracy": max(0, score),
            "feedback": feedback,
            "tts_candidate": tts,
            "animated_cue": animated_cue
        }

    def _eval_warrior2(self, lm: dict, metrics: dict) -> dict:
        """
        Warrior II:
        Wide stance. Front knee bent ~90° (75°-110°).
        Back leg straight (> 160°).
        Both arms extended horizontally parallel to floor (arm-torso ~80°-105°, elbow straight > 155°).
        """
        feedback = []
        cues = []
        score = 100

        l_knee = metrics["left"]["knee_angle"]
        r_knee = metrics["right"]["knee_angle"]

        # Determine front vs back leg
        if l_knee < r_knee:
            front_knee = l_knee
            back_knee = r_knee
            front_side = "left"
        else:
            front_knee = r_knee
            back_knee = l_knee
            front_side = "right"

        # Check front knee bend
        if front_knee > 120:
            score -= 30
            feedback.append(f"Bend your {front_side} front knee deeper toward 90°.")
            cues.append("Bend front knee lower ↓")
        elif front_knee < 70:
            score -= 20
            feedback.append("Don't let your front knee overshoot your ankle.")

        # Check back leg straightness
        if back_knee < 155:
            score -= 25
            feedback.append("Press your back leg straight and firm.")
            cues.append("Straighten back leg →")

        # Check horizontal arms
        l_arm = metrics["left"]["arm_torso_angle"]
        r_arm = metrics["right"]["arm_torso_angle"]
        if l_arm < 70 or r_arm < 70:
            score -= 25
            feedback.append("Raise both arms parallel to the floor.")
            cues.append("Raise arms horizontally ↔")

        is_aligned = score >= 70
        tts = "Good warrior alignment, hold strong." if is_aligned else (feedback[0] if feedback else None)
        animated_cue = {"type": "arrow_down" if "lower" in (cues[0] if cues else "") else "arrow_up",
                        "direction": "down" if "lower" in (cues[0] if cues else "") else "up",
                        "text": cues[0]} if cues else None

        if is_aligned and not feedback:
            feedback.append("Strong Warrior II! Relax shoulders and hold.")

        return {
            "is_aligned": is_aligned,
            "accuracy": max(0, score),
            "feedback": feedback,
            "tts_candidate": tts,
            "animated_cue": animated_cue
        }

    def _eval_downward_dog(self, lm: dict, metrics: dict) -> dict:
        """
        Downward Dog:
        Inverted V.
        Hip angle (shoulder-hip-ankle) between 65° and 110°.
        Arms straight (elbow > 150°).
        Hips pushed high.
        """
        feedback = []
        cues = []
        score = 100

        plank_angle = metrics.get("plank_angle", 180.0)
        elbow_angle = metrics.get("elbow_angle", 180.0)
        knee_angle = metrics.get("knee_angle", 180.0)

        # Inverted V check: hip angle should be acute to right angle (~70°-105°)
        if plank_angle > 135:
            score -= 35
            feedback.append("Push your hips higher toward the ceiling.")
            cues.append("Push hips higher ↑")
        elif plank_angle < 60:
            score -= 20
            feedback.append("Open your stance slightly.")

        # Arm straightness check
        if elbow_angle < 145:
            score -= 25
            feedback.append("Press firmly into your hands and straighten your arms.")
            cues.append("Straighten arms ↑")

        # Leg straightness check
        if knee_angle < 140:
            score -= 20
            feedback.append("Press your heels toward the floor to lengthen legs.")

        is_aligned = score >= 70
        tts = "Good Downward Dog, lengthen your spine." if is_aligned else (feedback[0] if feedback else None)
        animated_cue = {"type": "arrow_up", "direction": "up", "text": cues[0]} if cues else None

        if is_aligned and not feedback:
            feedback.append("Great inverted V shape! Press chest toward thighs.")

        return {
            "is_aligned": is_aligned,
            "accuracy": max(0, score),
            "feedback": feedback,
            "tts_candidate": tts,
            "animated_cue": animated_cue
        }
