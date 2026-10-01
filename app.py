"""
app.py
ApexMotion - AI-Powered Personal Training & Body Tracking System
Flask Web Application & REST APIs.
"""

import os
import sys
import time
import json
import random
import warnings
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session
from werkzeug.utils import secure_filename

# Suppress unpickling version warnings
warnings.filterwarnings("ignore")

# Ensure core and repo modules are importable
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_SRC = os.path.join(_CURRENT_DIR, "Doomsday-Sports-ML-REPO", "src")
_REPO_DATA = os.path.join(_CURRENT_DIR, "Doomsday-Sports-ML-REPO", "data")

for p in [_CURRENT_DIR, _REPO_SRC]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from core.pose_engine import PoseEngine
from core.exercise_analyzer import ExerciseAnalyzer
from core.yoga_analyzer import YogaAnalyzer, YOGA_POSES_METADATA
from core.video_processor import VideoProcessor
from core.action_classifier import ActionClassifier
from core.database import (
    init_db, create_user, authenticate_user, get_user_by_id, get_user_by_email,
    add_workout, get_user_workouts, delete_workout, clear_user_workouts,
    seed_test_accounts
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'apexmotion-smart-coaching-secret-key-2026')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['UPLOAD_FOLDER'] = os.path.join(_CURRENT_DIR, 'static', 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(_CURRENT_DIR, 'static', 'outputs')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB max video upload

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize database and seed demo accounts
init_db()
seed_test_accounts()

# Shared instances for live sessions
pose_engine = PoseEngine(min_detection_confidence=0.5, min_tracking_confidence=0.5)
exercise_analyzer = ExerciseAnalyzer(exercise_type="squat")
yoga_analyzer = YogaAnalyzer(selected_pose="tadasana", target_hold_seconds=10)
video_processor = VideoProcessor(output_dir=app.config['OUTPUT_FOLDER'])

# Store latest summary for the summary view
latest_session_summary = {
    "exercise": "Squat",
    "exercises_completed": "20 Squats",
    "total_repetitions": 20,
    "good_repetitions": 17,
    "bad_repetitions": 3,
    "workout_duration": "04:32",
    "workout_duration_seconds": 272,
    "form_quality": "Good",
    "form_score_pct": 85.0,
    "most_common_issue": "Forward torso lean during lowering phase",
    "suggested_improvement": "Focus on keeping your chest upright during the lowering phase.",
    "why_it_matters": "Maintaining controlled alignment can reduce unnecessary strain during movement.",
    "visual_type": "squat_lean",
    "voice_instruction": "Keep your chest upright and back straight.",
    "suggested_next_workout": "Try controlled squats with slower movement and pause at parallel depth.",
    "training_adjustments": [
        "Technique Consistency High: Your movement mechanics were solid across repetitions.",
        "Postural Cue: Chest upright. Before descending, brace your core and look straight ahead."
    ],
    "voice_coaching": True
}


def login_required(f):
    """Protects routes so that unauthenticated users are redirected to login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or not get_user_by_id(session["user_id"]):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized. Please log in."}), 401
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_user():
    """Injects current_user into all rendered templates."""
    user = None
    if "user_id" in session:
        user = get_user_by_id(session["user_id"])
    return {"current_user": user}


# ---------------- AUTHENTICATION ROUTES ----------------

@app.route("/login")
def login():
    """Starting Login / Register authentication view."""
    if "user_id" in session and get_user_by_id(session["user_id"]):
        next_page = request.args.get("next") or url_for("index")
        return redirect(next_page)
    return render_template("auth.html")


@app.route("/register")
def register():
    """Shortcut redirect to register tab on auth screen."""
    return redirect(url_for("login", mode="register"))


@app.route("/logout")
def logout():
    """Logs out current user and returns to login screen."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """Authenticates user via email and password."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    user = authenticate_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    session["user_id"] = user["id"]
    return jsonify({
        "status": "success",
        "message": f"Welcome back, {user['name']}!",
        "user": user
    })


@app.route("/api/auth/register", methods=["POST"])
def api_register():
    """Registers a new user and logs them in."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not name:
        return jsonify({"error": "Please enter your name."}), 400
    if not email or "@" not in email or "." not in email:
        return jsonify({"error": "Please enter a valid email address."}), 400
    if not password:
        return jsonify({"error": "Password cannot be empty."}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters."}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    try:
        user = create_user(name, email, password)
        session["user_id"] = user["id"]
        return jsonify({
            "status": "success",
            "message": f"Account created! Welcome, {user['name']}.",
            "user": user
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/auth/me", methods=["GET"])
def api_current_user():
    """Returns the current authenticated user profile."""
    if "user_id" not in session:
        return jsonify({"authenticated": False, "user": None}), 200
    user = get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"authenticated": False, "user": None}), 200
    return jsonify({"authenticated": True, "user": user})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    """Ends current user session."""
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully."})


# ---------------- USER-SPECIFIC WORKOUT HISTORY APIS ----------------

@app.route("/api/history", methods=["GET"])
@login_required
def get_history_api():
    """Fetches private workout history for the currently logged-in user."""
    workouts = get_user_workouts(session["user_id"])
    return jsonify({"status": "success", "workouts": workouts})


@app.route("/api/history", methods=["POST"])
@login_required
def add_history_api():
    """Saves a workout record under the currently logged-in user."""
    data = request.get_json(silent=True) or {}
    exercise = data.get("exercise", "Squat")
    reps = data.get("reps", "0")
    duration = data.get("duration", "02:00")
    form_status = data.get("form_status", data.get("form", "Good"))
    detected_issues = data.get("detected_issues", "")
    feedback = data.get("feedback", "")

    workout = add_workout(
        user_id=session["user_id"],
        exercise=exercise,
        reps=reps,
        duration=duration,
        form_status=form_status,
        detected_issues=detected_issues,
        feedback=feedback
    )
    return jsonify({"status": "success", "workout": workout}), 201


@app.route("/api/history/<int:workout_id>", methods=["DELETE"])
@login_required
def delete_history_item_api(workout_id):
    """Deletes a workout record only if it belongs to the current user."""
    success = delete_workout(session["user_id"], workout_id)
    if success:
        return jsonify({"status": "success", "message": "Workout deleted."})
    return jsonify({"error": "Workout not found or unauthorized."}), 404


@app.route("/api/history", methods=["DELETE"])
@login_required
def clear_history_api():
    """Clears all workouts belonging only to the current user."""
    count = clear_user_workouts(session["user_id"])
    return jsonify({"status": "success", "deleted_count": count})


# ---------------- PROTECTED APPLICATION ROUTES ----------------

@app.route("/")
@login_required
def index():
    """ApexMotion Dashboard & Home landing page."""
    return render_template("index.html")


@app.route("/live")
@login_required
def live_training():
    """Live camera training page with skeleton, rep counter, form reader, and voice coach."""
    return render_template("live.html")


@app.route("/yoga")
@login_required
def yoga_trainer():
    """Yoga trainer page with pose selection, alignment comparison, and hold timer."""
    return render_template("yoga.html", poses=YOGA_POSES_METADATA)


@app.route("/video")
@login_required
def video_analysis():
    """Pre-recorded video analysis page with upload and instant sample video demo."""
    sample_videos = get_available_sample_videos()
    return render_template("video_analysis.html", sample_videos=sample_videos)


@app.route("/summary")
@login_required
def summary():
    """Training summary page displaying workout results and suggestions."""
    return render_template("summary.html", summary=latest_session_summary)


# ---------------- STATIC ASSET ROUTE FOR SAMPLE VIDEOS ----------------

@app.route("/static/sample/<path:filename>")
def serve_sample_video(filename):
    """Safely serves sample demo video files with proper MIME types."""
    possible_dirs = [_REPO_DATA, os.path.join(_CURRENT_DIR, "data")]
    for d in possible_dirs:
        file_path = os.path.join(d, filename)
        if os.path.exists(file_path):
            return send_from_directory(d, filename, mimetype="video/mp4")
    return jsonify({"error": "Sample video not found"}), 404


# ---------------- API ENDPOINTS ----------------

@app.route("/api/process_frame", methods=["POST"])
def process_frame():
    """
    Live Camera API:
    Receives base64 image frame from client camera.
    Returns detected landmarks, angles, reps, form status, feedback, animated cues, and TTS prompt.
    """
    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image")
    exercise_type = data.get("exercise", "squat")

    if not image_b64:
        return jsonify({"error": "No image data provided"}), 400

    if exercise_analyzer.exercise_type != exercise_type.lower():
        exercise_analyzer.set_exercise(exercise_type)

    try:
        frame = pose_engine.decode_base64_image(image_b64)
        if frame is None:
            return jsonify({"error": "Failed to decode image"}), 400

        results, lm_dict, metrics = pose_engine.process_frame(frame)

        if not lm_dict or not metrics:
            return jsonify({
                "body_detected": False,
                "exercise": exercise_type,
                "reps": exercise_analyzer.rep_counter,
                "good_reps": exercise_analyzer.good_reps,
                "bad_reps": exercise_analyzer.bad_reps,
                "form_status": "WAITING FOR BODY",
                "feedback": ["Position your full body inside the camera frame."],
                "animated_cue": None,
                "tts_prompt": None,
                "landmarks": None,
                "angles": {}
            })

        analysis = exercise_analyzer.analyze(metrics)

        # Simplify landmarks payload to keep network payload lightweight
        simplified_landmarks = []
        for idx in range(33):
            if idx in lm_dict:
                lm = lm_dict[idx]
                simplified_landmarks.append({
                    "id": idx,
                    "x": round(lm["x"], 4),
                    "y": round(lm["y"], 4),
                    "v": round(lm["visibility"], 2)
                })

        return jsonify({
            "body_detected": True,
            "exercise": analysis["exercise"],
            "detected_ml_action": analysis.get("detected_ml_action", ""),
            "reps": analysis["reps"],
            "good_reps": analysis["good_reps"],
            "bad_reps": analysis["bad_reps"],
            "stage": analysis["stage"],
            "form_status": analysis["form_status"],
            "feedback": analysis["feedback"],
            "animated_cue": analysis["animated_cue"],
            "tts_prompt": analysis["tts_prompt"],
            "landmarks": simplified_landmarks,
            "angles": analysis["angles"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset_exercise", methods=["POST"])
def reset_exercise():
    """Resets workout counter and issues history."""
    data = request.get_json(silent=True) or {}
    exercise_type = data.get("exercise", "squat")
    exercise_analyzer.set_exercise(exercise_type)
    exercise_analyzer.reset()
    return jsonify({"status": "success", "reps": 0})


@app.route("/api/save_summary", methods=["POST"])
def save_summary():
    """Saves session summary when finishing workout."""
    global latest_session_summary
    data = request.get_json(silent=True) or {}
    duration_seconds = int(data.get("duration_seconds", 60))
    voice_enabled = data.get("voice_enabled", True)
    
    post_summary = exercise_analyzer.generate_post_workout_summary(duration_seconds)
    post_summary["voice_coaching"] = voice_enabled

    latest_session_summary = post_summary

    # Auto-save to current user database if authenticated
    if "user_id" in session and post_summary.get("total_repetitions", 0) > 0:
        try:
            add_workout(
                user_id=session["user_id"],
                exercise=exercise_analyzer.exercise_type.capitalize(),
                reps=str(post_summary.get("total_repetitions", 0)),
                duration=post_summary.get("workout_duration", "02:00"),
                form_status=post_summary.get("form_quality", "Good"),
                detected_issues=post_summary.get("most_common_issue", ""),
                feedback=post_summary.get("suggested_improvement", "")
            )
        except Exception as save_err:
            app.logger.warning(f"Could not auto-save live workout: {save_err}")

    return jsonify({"status": "success", "summary": post_summary, "redirect": "/summary"})


@app.route("/api/process_yoga_frame", methods=["POST"])
def process_yoga_frame():
    """
    Yoga Live Camera API:
    Receives base64 image and target pose name.
    Returns alignment status, accuracy score, feedback, hold timer, and animated cues.
    """
    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image")
    pose_name = data.get("pose", "tadasana")
    target_hold = int(data.get("target_hold", 10))

    if not image_b64:
        return jsonify({"error": "No image data provided"}), 400

    yoga_analyzer.set_pose(pose_name)
    yoga_analyzer.target_hold_seconds = target_hold

    try:
        frame = pose_engine.decode_base64_image(image_b64)
        if frame is None:
            return jsonify({"error": "Failed to decode image"}), 400

        results, lm_dict, metrics = pose_engine.process_frame(frame)

        if not lm_dict or not metrics:
            return jsonify({
                "body_detected": False,
                "pose": pose_name,
                "status": "WAITING FOR BODY",
                "accuracy": 0,
                "feedback": ["Position your full body inside the camera view."],
                "is_holding": False,
                "hold_duration": 0.0,
                "target_hold": target_hold,
                "hold_completed": False,
                "tts_prompt": None,
                "animated_cue": None,
                "landmarks": None
            })

        analysis = yoga_analyzer.analyze(lm_dict, metrics)

        simplified_landmarks = []
        for idx in range(33):
            if idx in lm_dict:
                lm = lm_dict[idx]
                simplified_landmarks.append({
                    "id": idx,
                    "x": round(lm["x"], 4),
                    "y": round(lm["y"], 4),
                    "v": round(lm["visibility"], 2)
                })

        return jsonify({
            "body_detected": True,
            "pose": analysis["pose"],
            "pose_name": analysis["pose_name"],
            "status": analysis["status"],
            "accuracy": analysis["accuracy"],
            "feedback": analysis["feedback"],
            "is_holding": analysis["is_holding"],
            "hold_duration": analysis["hold_duration"],
            "best_hold_duration": analysis["best_hold_duration"],
            "target_hold": analysis["target_hold"],
            "hold_completed": analysis["hold_completed"],
            "tts_prompt": analysis["tts_prompt"],
            "animated_cue": analysis["animated_cue"],
            "landmarks": simplified_landmarks
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset_yoga", methods=["POST"])
def reset_yoga():
    """Resets yoga timer and hold status."""
    yoga_analyzer.reset()
    return jsonify({"status": "success"})


@app.route("/api/analyze_video", methods=["POST"])
def analyze_video_endpoint():
    """
    Video Upload Analysis API:
    Supports uploading an MP4/MOV/WebM file OR selecting one of the repository sample videos.
    """
    global latest_session_summary
    uploaded_file = request.files.get("video_file")
    sample_filename = request.form.get("sample_filename")
    exercise_type = request.form.get("exercise_type", "auto")

    video_path = None

    if sample_filename:
        possible_paths = [
            os.path.join(_REPO_DATA, sample_filename),
            os.path.join(_CURRENT_DIR, "data", sample_filename)
        ]
        for p in possible_paths:
            if os.path.exists(p):
                video_path = p
                break
        if not video_path:
            return jsonify({"error": f"Sample video not found: {sample_filename}"}), 404

    elif uploaded_file and uploaded_file.filename:
        filename = secure_filename(uploaded_file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        uploaded_file.save(save_path)
        video_path = save_path

    else:
        return jsonify({"error": "Please provide a video file or choose a sample video"}), 400

    try:
        report = video_processor.process_video(video_path, exercise_type=exercise_type)
        if "post_workout_summary" in report:
            latest_session_summary = report["post_workout_summary"]
            latest_session_summary["voice_coaching"] = True

        # Auto-save to current user database if authenticated
        if "user_id" in session:
            try:
                corr = report.get("detailed_correction", {})
                add_workout(
                    user_id=session["user_id"],
                    exercise=report.get("exercise_detected", "Squat"),
                    reps=str(report.get("total_repetitions", 0)),
                    duration=report.get("video_duration", "02:00"),
                    form_status=report.get("form_quality", "Good"),
                    detected_issues=", ".join(report.get("form_issues", [])) or corr.get("detected_issue", ""),
                    feedback="; ".join(report.get("suggested_corrections", [])) or corr.get("how_to_correct", "")
                )
            except Exception as save_err:
                app.logger.warning(f"Could not auto-save video workout: {save_err}")

        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate_plan", methods=["GET"])
def generate_workout_plan():
    """
    Random Exercise Plan Generator:
    Generates balanced workout routines featuring squats, push-ups, lunges,
    planks, jumping jacks, and yoga postures with sets, reps/duration, and rest intervals.
    """
    POOL_EXERCISES = [
        {"name": "Bodyweight Squats", "category": "Lower Body", "sets": 3, "reps": "12 reps", "rest": "60 sec", "tip": "Focus on upright chest and parallel depth."},
        {"name": "Standard Push-ups", "category": "Upper Body", "sets": 3, "reps": "10 reps", "rest": "45 sec", "tip": "Maintain straight plank line from shoulders to heels."},
        {"name": "Walking Lunges", "category": "Lower Body", "sets": 3, "reps": "10 each leg", "rest": "45 sec", "tip": "Step forward with 90° front knee bend."},
        {"name": "Forearm Plank", "category": "Core", "sets": 3, "reps": "30 sec hold", "rest": "30 sec", "tip": "Brace core muscles and avoid sagging hips."},
        {"name": "Jumping Jacks", "category": "Cardio", "sets": 3, "reps": "45 sec", "rest": "30 sec", "tip": "Land lightly on balls of feet."},
        {"name": "Tadasana (Mountain Pose)", "category": "Yoga / Posture", "sets": 2, "reps": "30 sec hold", "rest": "15 sec", "tip": "Lengthen spine and level shoulders."},
        {"name": "Warrior II (Virabhadrasana)", "category": "Yoga / Mobility", "sets": 2, "reps": "20 sec each side", "rest": "20 sec", "tip": "Deep 90° front knee with arms parallel."},
        {"name": "Downward Dog", "category": "Yoga / Mobility", "sets": 2, "reps": "30 sec hold", "rest": "20 sec", "tip": "Push hips high and press heels toward floor."}
    ]

    # Select 4 or 5 balanced exercises
    selected = random.sample(POOL_EXERCISES, 4)
    total_est_minutes = random.randint(14, 20)

    return jsonify({
        "plan_title": "ApexMotion Balanced Full-Body Routine",
        "estimated_duration": f"{total_est_minutes} minutes",
        "exercises": selected,
        "difficulty": random.choice(["Moderate", "Balanced Endurance", "Dynamic Strength"]),
        "generated_at": time.strftime("%H:%M:%S")
    })


def get_available_sample_videos():
    """Returns sample videos already in the repository data folder."""
    samples = []
    data_dirs = [_REPO_DATA, os.path.join(_CURRENT_DIR, "data")]
    for d in data_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith((".mp4", ".mov", ".webm")) and not f.startswith("output"):
                    samples.append({
                        "filename": f,
                        "label": f.replace("test_", "").replace(".mp4", "").replace("_", " ").title() + " Demo Video"
                    })
            if samples:
                break
    return samples


if __name__ == "__main__":
    print("\n=======================================================")
    print("   ApexMotion - Smart Personal Training & Coach")
    print("   Local Server: http://127.0.0.1:5000")
    print("=======================================================\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
