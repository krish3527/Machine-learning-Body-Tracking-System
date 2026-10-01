"""
core/exercise_analyzer.py
Biomechanical exercise state machine, repetition counter, posture/form analyzer,
actionable coaching generator, and visual correction cue producer.
Supports Squat, Push-up, and ML Auto-Detection via action_model.pkl.
"""

import time
from typing import Dict, Any, List, Optional
from core.action_classifier import ActionClassifier


class ExerciseAnalyzer:
    def __init__(self, exercise_type: str = "squat"):
        self.exercise_type = exercise_type.lower()  # 'squat', 'pushup', or 'auto'
        self.classifier = ActionClassifier()
        
        # State machine variables
        self.stage: Optional[str] = None  # 'up', 'descending', 'bottom'/'down', 'ascending'
        self.rep_counter: int = 0
        self.good_reps: int = 0
        self.bad_reps: int = 0
        
        # Tracking history for current rep
        self.min_knee_angle_in_rep: float = 180.0
        self.min_elbow_angle_in_rep: float = 180.0
        self.max_torso_angle_in_rep: float = 0.0
        self.min_plank_angle_in_rep: float = 180.0
        self.max_knee_shift_in_rep: float = 0.0
        self.current_rep_issues: List[str] = []
        
        # All logged issues across session
        self.all_issues: List[str] = []
        self.rep_history: List[Dict[str, Any]] = []

        # Real-time state
        self.current_form_status: str = "GOOD FORM"
        self.current_feedback: List[str] = []
        self.current_animated_cue: Optional[Dict[str, str]] = None
        self.last_tts_message: Optional[str] = None
        self.last_tts_time: float = 0.0
        self.tts_cooldown: float = 3.5  # seconds cooldown between voice prompts

        # Stability buffer for ML auto-detect
        self.detected_action_history: List[str] = []

    def reset(self):
        """Resets all counter and form state for a fresh workout session."""
        self.stage = None
        self.rep_counter = 0
        self.good_reps = 0
        self.bad_reps = 0
        self.min_knee_angle_in_rep = 180.0
        self.min_elbow_angle_in_rep = 180.0
        self.max_torso_angle_in_rep = 0.0
        self.min_plank_angle_in_rep = 180.0
        self.max_knee_shift_in_rep = 0.0
        self.current_rep_issues = []
        self.all_issues = []
        self.rep_history = []
        self.current_form_status = "GOOD FORM"
        self.current_feedback = ["Get in position to begin."]
        self.current_animated_cue = None
        self.last_tts_message = None
        self.last_tts_time = 0.0
        self.detected_action_history = []

    def set_exercise(self, exercise_type: str):
        if self.exercise_type != exercise_type.lower():
            self.exercise_type = exercise_type.lower()
            self.reset()

    def analyze(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main analysis method called on every frame.
        Takes computed biomechanical angles and coordinates,
        updates state machine, counts reps, checks form, and returns coaching directives.
        """
        if not metrics:
            return {
                "exercise": self.exercise_type,
                "reps": self.rep_counter,
                "good_reps": self.good_reps,
                "bad_reps": self.bad_reps,
                "stage": self.stage or "waiting",
                "form_status": "WAITING",
                "feedback": ["Position your full body in camera view."],
                "animated_cue": None,
                "tts_prompt": None,
                "angles": {}
            }

        knee_angle = metrics.get("knee_angle", 180.0)
        elbow_angle = metrics.get("elbow_angle", 180.0)
        hip_angle = metrics.get("hip_angle", 180.0)
        plank_angle = metrics.get("plank_angle", 180.0)
        torso_angle = metrics.get("torso_angle", 0.0)
        arm_torso_angle = metrics.get("arm_torso_angle", 0.0)
        knee_shift = metrics.get("knee_lateral_shift", 0.0)

        # 1. Action Classification using ML Model
        ml_action, confidence, _ = self.classifier.predict(knee_angle, elbow_angle, hip_angle)
        self.detected_action_history.append(ml_action)
        if len(self.detected_action_history) > 15:
            self.detected_action_history.pop(0)

        # Determine effective exercise mode
        active_exercise = self.exercise_type
        if active_exercise == "auto":
            # Majority vote over last few frames
            from collections import Counter
            counts = Counter(self.detected_action_history)
            most_common = counts.most_common(1)[0][0]
            active_exercise = most_common if most_common in ["squat", "pushup"] else "squat"

        # 2. Run specific exercise state machine & form evaluation
        tts_candidate = None
        if active_exercise == "squat":
            tts_candidate = self._process_squat(knee_angle, hip_angle, torso_angle, knee_shift)
        elif active_exercise == "pushup":
            tts_candidate = self._process_pushup(elbow_angle, hip_angle, plank_angle, arm_torso_angle)
        else:
            self.current_form_status = "GOOD FORM"
            self.current_feedback = ["Standing ready. Start squats or pushups."]
            self.current_animated_cue = None

        # 3. Handle TTS Cooldown
        tts_to_speak = None
        now = time.time()
        if tts_candidate and (now - self.last_tts_time > self.tts_cooldown or "Good rep" in tts_candidate):
            # Only speak if message changed or cooldown passed
            if tts_candidate != self.last_tts_message or (now - self.last_tts_time > self.tts_cooldown * 1.5):
                tts_to_speak = tts_candidate
                self.last_tts_message = tts_candidate
                self.last_tts_time = now

        return {
            "exercise": active_exercise,
            "detected_ml_action": ml_action,
            "reps": self.rep_counter,
            "good_reps": self.good_reps,
            "bad_reps": self.bad_reps,
            "stage": self.stage or "start",
            "form_status": self.current_form_status,
            "feedback": self.current_feedback,
            "animated_cue": self.current_animated_cue,
            "tts_prompt": tts_to_speak,
            "angles": {
                "knee": knee_angle,
                "elbow": elbow_angle,
                "hip": hip_angle,
                "torso": torso_angle,
                "plank": plank_angle
            }
        }

    def _process_squat(self, knee_angle: float, hip_angle: float, torso_angle: float, knee_shift: float) -> Optional[str]:
        """
        Squat State Machine:
        standing (knee > 155) -> descending -> bottom (knee <= 100) -> ascending -> standing (knee > 155) [REP COMPLETE]
        """
        tts_prompt = None
        feedback_list = []
        animated_cue = None
        form_status = "GOOD FORM"

        # Update per-rep peak trackers
        if knee_angle < self.min_knee_angle_in_rep:
            self.min_knee_angle_in_rep = knee_angle
        if torso_angle > self.max_torso_angle_in_rep:
            self.max_torso_angle_in_rep = torso_angle
        if knee_shift > self.max_knee_shift_in_rep:
            self.max_knee_shift_in_rep = knee_shift

        # Form checks in real-time
        # Check 1: Torso angle / back straightness (excessive forward lean)
        if torso_angle > 38.0 and knee_angle < 140.0:
            form_status = "NEEDS CORRECTION"
            feedback_list.append("Keep your back straighter and chest up.")
            animated_cue = {
                "type": "arrow_up",
                "direction": "up",
                "text": "Straighten back ↑"
            }
            tts_prompt = "Keep your back straight."

        # Check 2: Knee tracking alignment
        if knee_shift > 35.0 and knee_angle < 130.0:
            form_status = "NEEDS CORRECTION"
            feedback_list.append("Keep your knees aligned with your feet.")
            if not animated_cue:
                animated_cue = {
                    "type": "arrow_right",
                    "direction": "right",
                    "text": "Keep knees aligned →"
                }
            if not tts_prompt:
                tts_prompt = "Keep your knees aligned."

        # State Machine Transitions
        if self.stage is None or self.stage == "standing":
            if knee_angle > 155.0:
                self.stage = "standing"
                if not feedback_list:
                    feedback_list.append("Ready. Begin descent by bending knees.")
            elif knee_angle < 140.0:
                self.stage = "descending"
                self.min_knee_angle_in_rep = knee_angle
                self.max_torso_angle_in_rep = torso_angle
                self.max_knee_shift_in_rep = knee_shift

        elif self.stage == "descending":
            if knee_angle <= 100.0:
                self.stage = "bottom"
                feedback_list.insert(0, "Good depth reached! Drive through heels to rise.")
            elif knee_angle > 145.0:
                # User started descending but aborted before hitting bottom: partial rep
                self.stage = "standing"
                self.min_knee_angle_in_rep = 180.0
                feedback_list.append("Lower your hips slightly to complete full depth.")
                animated_cue = {"type": "arrow_down", "direction": "down", "text": "Move hips lower ↓"}
                tts_prompt = "Lower your hips."

        elif self.stage == "bottom":
            if knee_angle > 115.0:
                self.stage = "ascending"
            else:
                feedback_list.insert(0, "Hold depth and press back up.")

        elif self.stage == "ascending":
            if knee_angle > 155.0:
                # COMPLETED REP!
                self.rep_counter += 1
                rep_is_good = True
                rep_issues = []

                # Final evaluation of completed rep
                if self.min_knee_angle_in_rep > 102.0:
                    rep_is_good = False
                    rep_issues.append("Shallow depth")
                    self.all_issues.append("Squat depth was too shallow")
                
                if self.max_torso_angle_in_rep > 40.0:
                    rep_is_good = False
                    rep_issues.append("Excessive torso lean")
                    self.all_issues.append("Excessive forward torso lean")

                if self.max_knee_shift_in_rep > 40.0:
                    rep_is_good = False
                    rep_issues.append("Knee misalignment")
                    self.all_issues.append("Knees caved inward")

                if rep_is_good:
                    self.good_reps += 1
                    tts_prompt = f"Good repetition, {self.rep_counter}."
                    feedback_list = [f"Rep {self.rep_counter} complete: Excellent form!"]
                    animated_cue = {"type": "check", "direction": "none", "text": "Good Form ✓"}
                else:
                    self.bad_reps += 1
                    tts_prompt = f"Rep {self.rep_counter}: {rep_issues[0]}."
                    feedback_list = [f"Rep {self.rep_counter} counted with form warning: {', '.join(rep_issues)}."]

                self.rep_history.append({
                    "rep_number": self.rep_counter,
                    "exercise": "squat",
                    "good": rep_is_good,
                    "min_angle": round(self.min_knee_angle_in_rep, 1),
                    "issues": rep_issues
                })

                # Reset for next rep
                self.stage = "standing"
                self.min_knee_angle_in_rep = 180.0
                self.max_torso_angle_in_rep = 0.0
                self.max_knee_shift_in_rep = 0.0

        if not feedback_list:
            feedback_list.append("Keep your chest upright and knees aligned.")

        self.current_form_status = form_status
        self.current_feedback = feedback_list[:2]  # Max 1-2 actionable tips
        self.current_animated_cue = animated_cue
        return tts_prompt

    def _process_pushup(self, elbow_angle: float, hip_angle: float, plank_angle: float, arm_torso_angle: float) -> Optional[str]:
        """
        Push-up State Machine:
        up (elbow > 155) -> descending -> down (elbow <= 95) -> ascending -> up (elbow > 155) [REP COMPLETE]
        """
        tts_prompt = None
        feedback_list = []
        animated_cue = None
        form_status = "GOOD FORM"

        if elbow_angle < self.min_elbow_angle_in_rep:
            self.min_elbow_angle_in_rep = elbow_angle
        if plank_angle < self.min_plank_angle_in_rep:
            self.min_plank_angle_in_rep = plank_angle

        # Form checks in real-time
        # Check 1: Sagging Hips (Plank line angle < 155°)
        if plank_angle < 155.0:
            form_status = "NEEDS CORRECTION"
            feedback_list.append("Don't let your hips sag. Engage your core.")
            animated_cue = {
                "type": "arrow_up",
                "direction": "up",
                "text": "Raise hips ↑"
            }
            tts_prompt = "Raise your hips."

        # Check 2: Piking Hips (Hip angle < 145° while hips raised)
        elif plank_angle > 195.0 or hip_angle < 145.0:
            form_status = "NEEDS CORRECTION"
            feedback_list.append("Lower your hips to maintain a straight plank.")
            animated_cue = {
                "type": "arrow_down",
                "direction": "down",
                "text": "Lower hips to plank ↓"
            }
            tts_prompt = "Keep your body in a straight line."

        # Check 3: Flaring Elbows (arm to torso angle > 75°)
        if arm_torso_angle > 75.0 and elbow_angle < 130.0:
            feedback_list.append("Keep your elbows closer to your body (~45° angle).")
            if not animated_cue:
                animated_cue = {
                    "type": "arrow_in",
                    "direction": "inward",
                    "text": "Tuck elbows inward ↔"
                }
            if not tts_prompt:
                tts_prompt = "Keep your elbows closer to your body."

        # State Machine Transitions
        if self.stage is None or self.stage == "up":
            if elbow_angle > 155.0:
                self.stage = "up"
                if not feedback_list:
                    feedback_list.append("In plank position. Lower chest toward floor.")
            elif elbow_angle < 135.0:
                self.stage = "descending"
                self.min_elbow_angle_in_rep = elbow_angle

        elif self.stage == "descending":
            if elbow_angle <= 95.0:
                self.stage = "down"
                feedback_list.insert(0, "Good chest depth! Push firmly away from floor.")
            elif elbow_angle > 145.0:
                # Aborted rep
                self.stage = "up"
                self.min_elbow_angle_in_rep = 180.0
                feedback_list.append("Lower your body closer to the floor for full rep.")
                animated_cue = {"type": "arrow_down", "direction": "down", "text": "Lower body ↓"}
                tts_prompt = "Lower your body."

        elif self.stage == "down":
            if elbow_angle > 115.0:
                self.stage = "ascending"

        elif self.stage == "ascending":
            if elbow_angle > 155.0:
                # COMPLETED REP!
                self.rep_counter += 1
                rep_is_good = True
                rep_issues = []

                if self.min_elbow_angle_in_rep > 100.0:
                    rep_is_good = False
                    rep_issues.append("Incomplete depth")
                    self.all_issues.append("Push-up depth was shallow")

                if self.min_plank_angle_in_rep < 155.0:
                    rep_is_good = False
                    rep_issues.append("Hips sagging")
                    self.all_issues.append("Hips sagged during push-up")

                if rep_is_good:
                    self.good_reps += 1
                    tts_prompt = f"Good repetition, {self.rep_counter}."
                    feedback_list = [f"Rep {self.rep_counter} complete: Clean push-up!"]
                    animated_cue = {"type": "check", "direction": "none", "text": "Good Form ✓"}
                else:
                    self.bad_reps += 1
                    tts_prompt = f"Rep {self.rep_counter}: {rep_issues[0]}."
                    feedback_list = [f"Rep {self.rep_counter} counted with form warning: {', '.join(rep_issues)}."]

                self.rep_history.append({
                    "rep_number": self.rep_counter,
                    "exercise": "pushup",
                    "good": rep_is_good,
                    "min_angle": round(self.min_elbow_angle_in_rep, 1),
                    "issues": rep_issues
                })

                # Reset for next rep
                self.stage = "up"
                self.min_elbow_angle_in_rep = 180.0
                self.min_plank_angle_in_rep = 180.0

        if not feedback_list:
            feedback_list.append("Maintain straight body line and steady rhythm.")

        self.current_form_status = form_status
        self.current_feedback = feedback_list[:2]
        self.current_animated_cue = animated_cue
        return tts_prompt

    def generate_training_adjustments(self) -> List[str]:
        """
        Generates practical training adjustment suggestions based on session metrics.
        Framed as general training guidance, NOT medical advice.
        """
        suggestions = []
        total_reps = self.rep_counter

        if total_reps == 0:
            return ["Complete at least 3 to 5 repetitions to receive personalized training adjustments."]

        form_ratio = self.good_reps / max(total_reps, 1)

        # 1. Intensity / Technique balance
        if form_ratio >= 0.85:
            suggestions.append(
                "Technique Consistency High: Your movement mechanics were solid across repetitions. "
                "Consider increasing repetitions gradually (+2-3 reps next set) or slowing your tempo."
            )
        elif form_ratio >= 0.60:
            suggestions.append(
                "Moderate Form Consistency: Several reps showed minor form breakdown. "
                "Maintain your current repetition volume and focus on strict range of motion before adding reps."
            )
        else:
            suggestions.append(
                "Technique Focus Recommended: Multiple repetitions deviated from optimal alignment. "
                "Reduce speed, decrease repetitions per set, and focus on full control through the movement."
            )

        # 2. Fatigue-specific recommendation
        if len(self.rep_history) >= 6:
            first_half = self.rep_history[:len(self.rep_history)//2]
            second_half = self.rep_history[len(self.rep_history)//2:]
            first_good = sum(1 for r in first_half if r["good"]) / len(first_half)
            second_good = sum(1 for r in second_half if r["good"]) / len(second_half)

            if first_good > 0.7 and second_good < 0.5:
                suggestions.append(
                    "Fatigue Management: Form deteriorated notably toward the end of your set. "
                    "Take a slightly longer rest interval (60-90 seconds) between sets to preserve movement quality."
                )

        # 3. Exercise-specific biomechanical guidance
        if self.exercise_type == "squat" or any("squat" in s.lower() for s in self.all_issues):
            if any("lean" in s.lower() for s in self.all_issues):
                suggestions.append(
                    "Postural Cue: Chest upright. Before descending, brace your core and look straight ahead to prevent forward lean."
                )
            if any("shallow" in s.lower() for s in self.all_issues):
                suggestions.append(
                    "Depth Cue: Work on hip mobility and ankle dorsiflexion stretches to achieve parallel depth comfortably."
                )
        elif self.exercise_type == "pushup" or any("pushup" in s.lower() for s in self.all_issues):
            if any("sag" in s.lower() for s in self.all_issues):
                suggestions.append(
                    "Core Engagement Cue: Squeeze your glutes and pull your navel inward to prevent hip sagging."
                )

        return suggestions

    def get_detailed_posture_correction(self) -> Dict[str, Any]:
        """
        Returns structured explanation of the most prominent posture issue:
        1. WHAT IS WRONG
        2. HOW TO CORRECT IT
        3. WHY IT MATTERS (Non-medical, joint alignment explanation)
        4. ANIMATED HUMAN SKELETON CORRECTION TYPE
        5. VOICE INSTRUCTION
        6. SUGGESTED NEXT WORKOUT
        """
        from collections import Counter
        most_common = None
        if self.all_issues:
            counts = Counter(self.all_issues)
            most_common = counts.most_common(1)[0][0]

        issue_lower = (most_common or "").lower()

        # Squat Forward Torso Lean
        if "lean" in issue_lower:
            return {
                "detected_issue": "Forward torso lean during lowering phase",
                "what_is_wrong": "Your torso is leaning too far forward during the squat.",
                "how_to_correct": "Keep your chest more upright and maintain a neutral back while lowering.",
                "why_it_matters": "Poor movement alignment can place unnecessary stress on joints and muscles. Better spinal alignment helps maintain controlled movement.",
                "visual_type": "squat_lean",
                "voice_instruction": "Keep your chest upright and back straight.",
                "suggested_next_workout": "Controlled bodyweight squats with a 3-second lowering tempo to reinforce torso stability."
            }

        # Squat Shallow Depth
        elif "shallow" in issue_lower and ("squat" in self.exercise_type or "depth" in issue_lower):
            return {
                "detected_issue": "Incomplete squat depth",
                "what_is_wrong": "You are stopping short of full depth before driving back upward.",
                "how_to_correct": "Lower your hips until your thighs are parallel to the floor (knee angle ~90°).",
                "why_it_matters": "Achieving balanced depth distributes movement force naturally across hips and knees, reducing localized patellar strain.",
                "visual_type": "squat_shallow",
                "voice_instruction": "Lower your hips slightly deeper.",
                "suggested_next_workout": "Box squats or goblet squats holding a light object to safely calibrate depth."
            }

        # Squat Knee Misalignment / Valgus
        elif "knee" in issue_lower or "cave" in issue_lower:
            return {
                "detected_issue": "Knees moving inward (valgus)",
                "what_is_wrong": "Your knees are caving inward rather than tracking in line with your feet.",
                "how_to_correct": "Actively push your knees outward so they track directly over your middle toes.",
                "why_it_matters": "Inward knee collapse can place unnecessary strain on ligaments. Keeping knees aligned preserves steady joint mechanics.",
                "visual_type": "squat_knee_valgus",
                "voice_instruction": "Keep your knees aligned with your feet.",
                "suggested_next_workout": "Banded squats and glute bridges to strengthen hip abductors."
            }

        # Push-up Sagging Hips
        elif "sag" in issue_lower or ("hip" in issue_lower and "pushup" in self.exercise_type):
            return {
                "detected_issue": "Hips dropping / sagging below plank line",
                "what_is_wrong": "Your hips are sagging downward, breaking the straight line from shoulders to ankles.",
                "how_to_correct": "Engage your core, squeeze your glutes, and raise your hips into a solid, straight plank.",
                "why_it_matters": "Sagging hips places unnecessary extension strain on the lower back and reduces core engagement.",
                "visual_type": "pushup_sagging_hips",
                "voice_instruction": "Engage your core and raise your hips.",
                "suggested_next_workout": "Incline push-ups on an elevated surface and 30-second forearm planks."
            }

        # Push-up Shallow Depth
        elif "depth" in issue_lower and "pushup" in self.exercise_type:
            return {
                "detected_issue": "Incomplete push-up range of motion",
                "what_is_wrong": "Chest did not reach full depth before pressing upward.",
                "how_to_correct": "Lower your chest until your elbows reach approximately 90 degrees.",
                "why_it_matters": "Full range of motion stimulates chest and triceps evenly and prevents excessive front shoulder loading.",
                "visual_type": "pushup_shallow",
                "voice_instruction": "Lower your chest closer to the floor.",
                "suggested_next_workout": "Knee push-ups with full chest-to-floor depth."
            }

        # Push-up Elbow Flare
        elif "elbow" in issue_lower:
            return {
                "detected_issue": "Elbows flaring excessively outward",
                "what_is_wrong": "Your elbows are pointing straight out at 90 degrees relative to your torso.",
                "how_to_correct": "Tuck your elbows closer to your ribs at roughly a 45-degree angle.",
                "why_it_matters": "Flaring elbows can pinch the anterior shoulder capsule and increase unnecessary joint stress.",
                "visual_type": "pushup_elbow_flare",
                "voice_instruction": "Keep your elbows closer to your body.",
                "suggested_next_workout": "Hand-release push-ups focusing on 45-degree elbow tuck."
            }

        # Yoga Alignment
        elif "yoga" in self.exercise_type or "yoga" in issue_lower:
            return {
                "detected_issue": "Yoga posture deviation / imbalance",
                "what_is_wrong": "Joint alignment and balance deviated from target yoga posture.",
                "how_to_correct": "Engage core, extend spine, and align joints according to the reference posture.",
                "why_it_matters": "Proper yoga alignment ensures balanced muscle activation and protects connective tissue.",
                "visual_type": "yoga_alignment",
                "voice_instruction": "Align your posture and hold your balance.",
                "suggested_next_workout": "Hold pose for 30-45 seconds focusing on deep diaphragmatic breathing."
            }

        # Clean / Good Form
        else:
            return {
                "detected_issue": "Solid technique maintained",
                "what_is_wrong": "No significant posture flaws detected.",
                "how_to_correct": "Maintain controlled tempo and full range of motion.",
                "why_it_matters": "Consistent movement mechanics allow safe, progressive training adaptation.",
                "visual_type": "clean",
                "voice_instruction": "Excellent form, keep up the good work.",
                "suggested_next_workout": "Gradual progression: add 2-3 reps next session or decrease rest interval by 15s."
            }

    def generate_post_workout_summary(self, duration_seconds: int = 0) -> Dict[str, Any]:
        """
        Produces clean Post Workout Summary meeting the exact required specifications:
        - Exercises completed
        - Total repetitions
        - Workout duration (MM:SS)
        - Form quality (Good / Needs Improvement)
        - Most common posture issue
        - Suggested improvement
        - Suggested next workout
        """
        mins = duration_seconds // 60
        secs = duration_seconds % 60
        duration_str = f"{mins:02d}:{secs:02d}"

        correction = self.get_detailed_posture_correction()
        total_reps = self.rep_counter
        form_ratio = (self.good_reps / max(total_reps, 1)) * 100
        form_quality = "Good" if form_ratio >= 70 else "Needs Improvement"

        exercises_completed_str = f"{total_reps} {self.exercise_type.capitalize()}s" if total_reps > 0 else f"{self.exercise_type.capitalize()}"

        return {
            "exercise": self.exercise_type.capitalize(),
            "exercises_completed": exercises_completed_str,
            "total_repetitions": total_reps,
            "good_repetitions": self.good_reps,
            "bad_repetitions": self.bad_reps,
            "workout_duration": duration_str,
            "workout_duration_seconds": duration_seconds,
            "form_quality": form_quality,
            "form_score_pct": round(form_ratio, 1),
            "most_common_issue": correction["detected_issue"],
            "suggested_improvement": correction["how_to_correct"],
            "why_it_matters": correction["why_it_matters"],
            "visual_type": correction["visual_type"],
            "voice_instruction": correction["voice_instruction"],
            "suggested_next_workout": correction["suggested_next_workout"],
            "training_adjustments": self.generate_training_adjustments()
        }
