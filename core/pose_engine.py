"""
core/pose_engine.py
MediaPipe Pose wrapper and biomechanical feature extractor.
Extracts 33 body landmarks, calculates joint angles via angle_utils.py,
determines body orientation, and provides clean visualization helpers.
"""

import os
import sys
import base64
import math
import cv2
import numpy as np
import mediapipe as mp

# Re-use angle calculation from existing repository
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


class PoseEngine:
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5, model_complexity=1):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity,
            static_image_mode=False
        )

    def decode_base64_image(self, base64_str: str) -> np.ndarray:
        """Decodes a base64 encoded data URI or raw string to a BGR numpy image."""
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        img_bytes = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame

    def encode_base64_image(self, frame: np.ndarray, quality=80) -> str:
        """Encodes a BGR numpy image to a JPEG base64 string."""
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_param)
        return base64.b64encode(buffer).decode('utf-8')

    def process_frame(self, frame: np.ndarray):
        """
        Runs MediaPipe pose estimation on BGR frame.
        Returns:
            results: MediaPipe raw output
            landmarks_dict: dict of 33 landmarks {id: {'x', 'y', 'z', 'visibility'}}
            metrics: dict of computed joint angles and alignment metrics
        """
        if frame is None:
            return None, None, None

        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.pose.process(rgb_frame)
        rgb_frame.flags.writeable = True

        if not results.pose_landmarks:
            return results, None, None

        raw_landmarks = results.pose_landmarks.landmark
        landmarks_dict = {}
        for idx, lm in enumerate(raw_landmarks):
            landmarks_dict[idx] = {
                "x": float(lm.x),
                "y": float(lm.y),
                "z": float(lm.z),
                "visibility": float(lm.visibility)
            }

        metrics = self.extract_biomechanical_metrics(landmarks_dict, w, h)
        return results, landmarks_dict, metrics

    def extract_biomechanical_metrics(self, lm_dict: dict, w: int, h: int) -> dict:
        """
        Calculates left & right joint angles and identifies primary view side.
        """
        # Key landmark indices (MediaPipe Pose specification)
        # Left side: Shoulder 11, Elbow 13, Wrist 15, Hip 23, Knee 25, Ankle 27, Heel 29, Index 31
        # Right side: Shoulder 12, Elbow 14, Wrist 16, Hip 24, Knee 26, Ankle 28, Heel 30, Index 32
        
        # Left side coordinates
        l_shoulder = [lm_dict[11]["x"], lm_dict[11]["y"]]
        l_elbow    = [lm_dict[13]["x"], lm_dict[13]["y"]]
        l_wrist    = [lm_dict[15]["x"], lm_dict[15]["y"]]
        l_hip      = [lm_dict[23]["x"], lm_dict[23]["y"]]
        l_knee     = [lm_dict[25]["x"], lm_dict[25]["y"]]
        l_ankle    = [lm_dict[27]["x"], lm_dict[27]["y"]]

        # Right side coordinates
        r_shoulder = [lm_dict[12]["x"], lm_dict[12]["y"]]
        r_elbow    = [lm_dict[14]["x"], lm_dict[14]["y"]]
        r_wrist    = [lm_dict[16]["x"], lm_dict[16]["y"]]
        r_hip      = [lm_dict[24]["x"], lm_dict[24]["y"]]
        r_knee     = [lm_dict[26]["x"], lm_dict[26]["y"]]
        r_ankle    = [lm_dict[28]["x"], lm_dict[28]["y"]]

        # Left side angles
        l_knee_angle   = calculate_angle(l_hip, l_knee, l_ankle)
        l_elbow_angle  = calculate_angle(l_shoulder, l_elbow, l_wrist)
        l_hip_angle    = calculate_angle(l_shoulder, l_hip, l_knee)
        l_plank_angle  = calculate_angle(l_shoulder, l_hip, l_ankle)  # Straight line check
        l_arm_torso    = calculate_angle(l_hip, l_shoulder, l_elbow)

        # Right side angles
        r_knee_angle   = calculate_angle(r_hip, r_knee, r_ankle)
        r_elbow_angle  = calculate_angle(r_shoulder, r_elbow, r_wrist)
        r_hip_angle    = calculate_angle(r_shoulder, r_hip, r_knee)
        r_plank_angle  = calculate_angle(r_shoulder, r_hip, r_ankle)
        r_arm_torso    = calculate_angle(r_hip, r_shoulder, r_elbow)

        # Determine visibility
        l_vis = (lm_dict[11]["visibility"] + lm_dict[13]["visibility"] + lm_dict[23]["visibility"] + lm_dict[25]["visibility"]) / 4.0
        r_vis = (lm_dict[12]["visibility"] + lm_dict[14]["visibility"] + lm_dict[24]["visibility"] + lm_dict[26]["visibility"]) / 4.0
        primary_side = "left" if l_vis >= r_vis else "right"

        # Select primary metrics matching existing repo feature format
        if primary_side == "left":
            knee_angle = l_knee_angle
            elbow_angle = l_elbow_angle
            hip_angle = l_hip_angle
            plank_angle = l_plank_angle
            arm_torso_angle = l_arm_torso
            shoulder_pt = l_shoulder
            hip_pt = l_hip
            knee_pt = l_knee
            ankle_pt = l_ankle
        else:
            knee_angle = r_knee_angle
            elbow_angle = r_elbow_angle
            hip_angle = r_hip_angle
            plank_angle = r_plank_angle
            arm_torso_angle = r_arm_torso
            shoulder_pt = r_shoulder
            hip_pt = r_hip
            knee_pt = r_knee
            ankle_pt = r_ankle

        # Torso inclination angle from vertical (0 deg = upright vertical, >35 deg = forward lean)
        # Vector from hip to shoulder:
        dx = (shoulder_pt[0] - hip_pt[0]) * w
        dy = (shoulder_pt[1] - hip_pt[1]) * h  # y increases downward in screen coords
        # dy is negative when shoulder is above hip
        torso_angle_from_vertical = abs(math.degrees(math.atan2(abs(dx), abs(dy) if abs(dy) > 1e-4 else 1e-4)))

        # Knee tracking / valgus estimation (horizontal alignment of knee between hip and ankle)
        knee_x = knee_pt[0]
        ankle_x = ankle_pt[0]
        hip_x = hip_pt[0]
        knee_lateral_shift = abs(knee_x - (hip_x + ankle_x) / 2.0) * w

        return {
            "primary_side": primary_side,
            "knee_angle": round(knee_angle, 1),
            "elbow_angle": round(elbow_angle, 1),
            "hip_angle": round(hip_angle, 1),
            "plank_angle": round(plank_angle, 1),
            "torso_angle": round(torso_angle_from_vertical, 1),
            "arm_torso_angle": round(arm_torso_angle, 1),
            "left": {
                "knee_angle": round(l_knee_angle, 1),
                "elbow_angle": round(l_elbow_angle, 1),
                "hip_angle": round(l_hip_angle, 1),
                "plank_angle": round(l_plank_angle, 1),
                "arm_torso_angle": round(l_arm_torso, 1),
            },
            "right": {
                "knee_angle": round(r_knee_angle, 1),
                "elbow_angle": round(r_elbow_angle, 1),
                "hip_angle": round(r_hip_angle, 1),
                "plank_angle": round(r_plank_angle, 1),
                "arm_torso_angle": round(r_arm_torso, 1),
            },
            "knee_lateral_shift": round(knee_lateral_shift, 1)
        }

    def draw_skeleton_overlay(self, frame: np.ndarray, results, metrics: dict = None, exercise_info: dict = None):
        """
        Draws clean, professional fitness app visual skeleton overlay.
        No sci-fi neon clutter; clean white/slate lines, crisp colored joint circles,
        and subtle status indicators.
        """
        if results is None or not results.pose_landmarks:
            return frame

        annotated_frame = frame.copy()
        h, w, _ = frame.shape

        # Clean professional colors
        LINE_COLOR = (240, 240, 240)       # Clean crisp white/slate
        JOINT_COLOR = (220, 100, 37)       # Athletic Blue BGR (RGB: 37, 100, 220)
        JOINT_CORE_COLOR = (255, 255, 255) # Clean White core
        GOOD_COLOR = (74, 180, 74)         # Green BGR
        WARN_COLOR = (50, 70, 220)         # Red/Amber BGR

        # Draw custom connections with controlled thickness
        connections = self.mp_pose.POSE_CONNECTIONS
        landmarks = results.pose_landmarks.landmark

        # Draw bones
        for connection in connections:
            start_idx, end_idx = connection
            pt1 = landmarks[start_idx]
            pt2 = landmarks[end_idx]
            if pt1.visibility > 0.4 and pt2.visibility > 0.4:
                x1, y1 = int(pt1.x * w), int(pt1.y * h)
                x2, y2 = int(pt2.x * w), int(pt2.y * h)
                cv2.line(annotated_frame, (x1, y1), (x2, y2), (40, 40, 40), 4, cv2.LINE_AA)
                cv2.line(annotated_frame, (x1, y1), (x2, y2), LINE_COLOR, 2, cv2.LINE_AA)

        # Draw key joints
        KEY_JOINTS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
        for idx in KEY_JOINTS:
            lm = landmarks[idx]
            if lm.visibility > 0.4:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(annotated_frame, (cx, cy), 6, JOINT_COLOR, -1, cv2.LINE_AA)
                cv2.circle(annotated_frame, (cx, cy), 3, JOINT_CORE_COLOR, -1, cv2.LINE_AA)

        # Draw on-frame HUD badge if exercise info provided
        if exercise_info:
            exercise_name = exercise_info.get("exercise", "Tracking").upper()
            reps = exercise_info.get("reps", 0)
            form_status = exercise_info.get("form_status", "READY").upper()
            is_good = "GOOD" in form_status

            # Top HUD Bar
            badge_color = (46, 139, 87) if is_good else (50, 50, 200) # Green or Red
            cv2.rectangle(annotated_frame, (16, 16), (280, 85), (20, 24, 30), -1)
            cv2.rectangle(annotated_frame, (16, 16), (280, 85), (200, 200, 200), 1)

            cv2.putText(annotated_frame, f"{exercise_name}", (26, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(annotated_frame, f"REPS: {reps}", (26, 72),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

            # Form pill
            cv2.rectangle(annotated_frame, (170, 28), (270, 72), badge_color, -1)
            pill_text = "GOOD" if is_good else "CORRECT"
            cv2.putText(annotated_frame, pill_text, (180, 56),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

        return annotated_frame

    def close(self):
        if self.pose:
            self.pose.close()
