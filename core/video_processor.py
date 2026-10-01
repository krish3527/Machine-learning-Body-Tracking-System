"""
core/video_processor.py
Pre-recorded video analyzer for workout and yoga movement analysis.
Processes MP4, MOV, and WebM videos using MediaPipe Pose, action classifier,
and exercise form analyzer. Outputs rep counts, form issues, coaching suggestions,
and training adjustment advice.
"""

import os
import time
from typing import Dict, Any, List
import cv2
import numpy as np

from core.pose_engine import PoseEngine
from core.exercise_analyzer import ExerciseAnalyzer
from core.action_classifier import ActionClassifier


class VideoProcessor:
    def __init__(self, output_dir: str = "static/outputs"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.pose_engine = PoseEngine(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def process_video(self, video_path: str, exercise_type: str = "auto", progress_callback=None) -> Dict[str, Any]:
        """
        Processes video file frame-by-frame.
        Extracts pose, detects exercise, tracks repetitions, flags form flaws,
        generates annotated video, and produces comprehensive training summary.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Handle zero or corrupted frame count
        if total_frames <= 0:
            total_frames = 300

        # Downscale for fast video processing if video is high-res (e.g. 1080p/4K)
        max_dim = 720
        scale = 1.0
        if max(width, height) > max_dim:
            scale = max_dim / float(max(width, height))
            target_w = int(width * scale)
            target_h = int(height * scale)
        else:
            target_w = width
            target_h = height

        # Output video filename
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        timestamp_str = int(time.time())
        output_filename = f"analyzed_{base_name}_{timestamp_str}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)

        # VideoWriter
        # Use mp4v or avc1
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, orig_fps, (target_w, target_h))

        analyzer = ExerciseAnalyzer(exercise_type=exercise_type)
        frame_idx = 0
        detected_actions_list = []
        fps_frame_step = 1  # Process every frame for high fidelity
        if total_frames > 600:
            fps_frame_step = 2  # Downsample frame rate for longer videos to keep processing fast

        start_time = time.time()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            if frame_idx % fps_frame_step != 0:
                continue

            if scale != 1.0:
                frame = cv2.resize(frame, (target_w, target_h))

            # Run pose detection
            results, lm_dict, metrics = self.pose_engine.process_frame(frame)

            if metrics:
                # Update analyzer
                analysis = analyzer.analyze(metrics)
                detected_actions_list.append(analysis["detected_ml_action"])

                # Draw clean HUD and skeleton on frame
                hud_info = {
                    "exercise": analysis["exercise"],
                    "reps": analysis["reps"],
                    "form_status": analysis["form_status"]
                }
                annotated = self.pose_engine.draw_skeleton_overlay(frame, results, metrics, hud_info)

                # Add coaching subtitle banner if feedback exists
                if analysis["feedback"]:
                    cv2.rectangle(annotated, (16, target_h - 45), (target_w - 16, target_h - 12), (20, 24, 30), -1)
                    cv2.putText(annotated, f"COACH: {analysis['feedback'][0]}", (26, target_h - 22),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
                
                out.write(annotated)
            else:
                out.write(frame)

            if progress_callback and frame_idx % 30 == 0:
                progress_callback(min(1.0, frame_idx / float(total_frames)))

        cap.release()
        out.release()
        elapsed = round(time.time() - start_time, 2)

        # Determine dominant exercise detected
        from collections import Counter
        if detected_actions_list:
            action_counts = Counter(detected_actions_list)
            # Filter out 'standing' if workout action exists
            workout_actions = [a for a in detected_actions_list if a in ["squat", "pushup"]]
            if workout_actions:
                dominant_exercise = Counter(workout_actions).most_common(1)[0][0]
            else:
                dominant_exercise = action_counts.most_common(1)[0][0]
        else:
            dominant_exercise = exercise_type if exercise_type != "auto" else "squat"

        # Unique form issues identified
        from collections import Counter
        issue_counts = dict(Counter(analyzer.all_issues))
        unique_issues = list(issue_counts.keys())
        
        # Build coaching recommendations
        suggested_corrections = []
        if any("shallow" in s.lower() for s in unique_issues):
            suggested_corrections.append("Focus on reaching full depth (thighs parallel to floor for squats, chest near floor for push-ups).")
        if any("lean" in s.lower() for s in unique_issues):
            suggested_corrections.append("Keep your chest upright and core braced to avoid forward spinal flexion.")
        if any("knee" in s.lower() for s in unique_issues):
            suggested_corrections.append("Push knees outward to align directly over your second toe throughout the movement.")
        if any("sag" in s.lower() for s in unique_issues):
            suggested_corrections.append("Engage your glutes and abdominal muscles to keep your spine in a neutral plank line.")

        if not suggested_corrections and analyzer.rep_counter > 0:
            suggested_corrections.append("Keep up the solid form and consistent tempo!")

        # Training adjustments (Rule-based fitness guidelines, NOT medical advice)
        training_adjustments = analyzer.generate_training_adjustments()

        # Video duration in seconds
        video_duration_sec = int(total_frames / max(orig_fps, 1))
        mins = video_duration_sec // 60
        secs = video_duration_sec % 60
        duration_str = f"{mins:02d}:{secs:02d}"

        # Detailed posture correction structure
        detailed_correction = analyzer.get_detailed_posture_correction()
        detailed_correction["exercise"] = dominant_exercise.lower()

        # Post workout summary
        post_summary = analyzer.generate_post_workout_summary(video_duration_sec)

        # Web-accessible URL for video
        web_video_url = f"/static/outputs/{output_filename}"
        
        # Original playable video URL (if in static/uploads or static/sample)
        filename_only = os.path.basename(video_path)
        if "uploads" in video_path:
            playable_url = f"/static/uploads/{filename_only}"
        else:
            playable_url = f"/static/sample/{filename_only}"

        return {
            "status": "success",
            "video_filename": filename_only,
            "playable_video_url": playable_url,
            "output_video_url": web_video_url,
            "processed_duration_seconds": elapsed,
            "video_duration": duration_str,
            "video_duration_seconds": video_duration_sec,
            "frames_analyzed": frame_idx,
            "exercise_detected": dominant_exercise.capitalize(),
            "total_repetitions": analyzer.rep_counter,
            "good_repetitions": analyzer.good_reps,
            "correction_needed_repetitions": analyzer.bad_reps,
            "form_score_pct": round((analyzer.good_reps / max(analyzer.rep_counter, 1)) * 100, 1),
            "form_quality": "Good" if (analyzer.good_reps / max(analyzer.rep_counter, 1)) >= 0.7 else "Needs Improvement",
            "form_issues": unique_issues,
            "issue_counts": issue_counts,
            "suggested_corrections": suggested_corrections,
            "training_adjustments": training_adjustments,
            "detailed_correction": detailed_correction,
            "post_workout_summary": post_summary,
            "rep_details": analyzer.rep_history
        }
