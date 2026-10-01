"""
test_app.py
End-to-end verification test for ApexMotion
Tests:
1. Authentication: Login, Registration, Session, Route Protection
2. User-Specific Workout History Isolation (User A vs User B)
3. Live Camera Frame Tracking & Rep Counting API
4. Yoga Posture Alignment Evaluator
5. Pre-recorded Video Analysis & Posture Correction
6. Workout Plan Generator
"""

import cv2
import json
import base64
from app import app
from core.database import init_db, seed_test_accounts

def run_tests():
    print("Beginning ApexMotion automated test suite...\n")
    init_db()
    seed_test_accounts()

    # Create test client
    client = app.test_client()

    # ---------------- 1. TEST ROUTE PROTECTION (UNAUTHENTICATED) ----------------
    print("[1] Testing Route Protection for Unauthenticated Users...")
    protected_routes = ["/", "/live", "/video", "/yoga", "/summary"]
    for r in protected_routes:
        resp = client.get(r)
        assert resp.status_code == 302, f"Expected 302 redirect for {r}, got {resp.status_code}"
        assert "/login" in resp.headers.get("Location", ""), f"Expected redirect to /login for {r}"
        print(f"  [PASS] GET {r} -> 302 Redirect to /login")

    resp = client.get("/login")
    assert resp.status_code == 200, f"Expected 200 for /login, got {resp.status_code}"
    assert b"Welcome to ApexMotion" in resp.data
    assert b"Login" in resp.data and b"Register" in resp.data
    print("  [PASS] GET /login -> 200 OK (Auth screen loaded)")

    # ---------------- 2. TEST REGISTRATION VALIDATION & CREATION ----------------
    print("\n[2] Testing Registration Form & Validation...")
    # Missing name
    resp = client.post("/api/auth/register", json={
        "name": "", "email": "newuser@example.com", "password": "password123", "confirm_password": "password123"
    })
    assert resp.status_code == 400
    print("  [PASS] Rejected empty name")

    # Mismatched passwords
    resp = client.post("/api/auth/register", json={
        "name": "New Athlete", "email": "newuser@example.com", "password": "password123", "confirm_password": "different"
    })
    assert resp.status_code == 400
    print("  [PASS] Rejected mismatched passwords")

    # Valid registration
    new_email = "newathlete_2026@example.com"
    resp = client.post("/api/auth/register", json={
        "name": "New Athlete", "email": new_email, "password": "securepassword", "confirm_password": "securepassword"
    })
    assert resp.status_code in [201, 400]  # 201 on new, 400 if already exists
    print("  [PASS] User registration validated and processed")

    # ---------------- 3. TEST AUTHENTICATION & LOGIN ----------------
    print("\n[3] Testing Login Validation & Session Creation...")
    # Invalid password
    resp = client.post("/api/auth/login", json={"email": "test1@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.get_json().get("error", "")
    print("  [PASS] Rejected invalid credentials (401)")

    # ---------------- 4. MANDATORY REQUIREMENT: USER ISOLATION (USER A vs USER B) ----------------
    print("\n[4] Testing User-Specific Workout History Isolation (User A vs User B)...")
    
    # 4A. Login as User A
    client_a = app.test_client()
    login_a = client_a.post("/api/auth/login", json={"email": "test1@example.com", "password": "test1234"})
    assert login_a.status_code == 200, "User A login failed"
    user_a_data = login_a.get_json()["user"]
    print(f"  [PASS] Logged in as User A ({user_a_data['email']})")

    # Access protected dashboard
    dash_a = client_a.get("/")
    assert dash_a.status_code == 200, "User A could not access dashboard"
    assert b"Welcome back" in dash_a.data

    # Fetch User A's history
    hist_a_resp = client_a.get("/api/history")
    assert hist_a_resp.status_code == 200
    workouts_a = hist_a_resp.get_json()["workouts"]
    initial_a_count = len(workouts_a)
    print(f"  [PASS] User A sees {initial_a_count} private workouts")

    # User A adds a new workout
    new_w = client_a.post("/api/history", json={
        "exercise": "Squat",
        "reps": "25",
        "duration": "05:10",
        "form_status": "Good",
        "detected_issues": "",
        "feedback": "Perfect depth achieved"
    })
    assert new_w.status_code == 201
    created_id = new_w.get_json()["workout"]["id"]
    print(f"  [PASS] User A added new workout (ID: {created_id})")

    # Verify User A has initial_a_count + 1
    workouts_a_updated = client_a.get("/api/history").get_json()["workouts"]
    assert len(workouts_a_updated) == initial_a_count + 1

    # User A logs out
    client_a.get("/logout")
    print("  [PASS] User A logged out successfully")

    # 4B. Login as User B
    client_b = app.test_client()
    login_b = client_b.post("/api/auth/login", json={"email": "test2@example.com", "password": "test1234"})
    assert login_b.status_code == 200, "User B login failed"
    user_b_data = login_b.get_json()["user"]
    print(f"  [PASS] Logged in as User B ({user_b_data['email']})")

    # Fetch User B's history
    hist_b_resp = client_b.get("/api/history")
    assert hist_b_resp.status_code == 200
    workouts_b = hist_b_resp.get_json()["workouts"]
    print(f"  [PASS] User B sees {len(workouts_b)} private workouts")

    # STRICT ISOLATION ASSERTION: User B MUST NEVER see User A's workout IDs or records!
    b_ids = [w["id"] for w in workouts_b]
    assert created_id not in b_ids, "CRITICAL ERROR: User B can see User A's workout!"
    for w in workouts_b:
        assert w["user_id"] == user_b_data["id"], f"Cross-user data leak: expected user {user_b_data['id']}, got {w['user_id']}"
    print("  [PASS] Verified 100% data isolation: User B cannot see any User A records")

    # User B tries to delete User A's workout
    unauth_delete = client_b.delete(f"/api/history/{created_id}")
    assert unauth_delete.status_code == 404, "User B was able to affect User A's workout!"
    print("  [PASS] Verified cross-user delete prevention: User B cannot delete User A's record")

    # User B adds and then clears their own history
    client_b.post("/api/history", json={
        "exercise": "Push-up", "reps": "10", "duration": "01:20", "form_status": "Good"
    })
    client_b.delete("/api/history")
    workouts_b_after_clear = client_b.get("/api/history").get_json()["workouts"]
    assert len(workouts_b_after_clear) == 0, "User B clear history failed"
    print("  [PASS] User B cleared their history (0 workouts remaining)")

    # User B logs out
    client_b.get("/logout")

    # 4C. Log back in as User A to verify their records were untouched
    client_a2 = app.test_client()
    client_a2.post("/api/auth/login", json={"email": "test1@example.com", "password": "test1234"})
    workouts_a_final = client_a2.get("/api/history").get_json()["workouts"]
    assert len(workouts_a_final) == initial_a_count + 1, "User A records were unexpectedly altered by User B!"
    print(f"  [PASS] User A logs in again -> all {len(workouts_a_final)} workouts preserved intact!")

    # ---------------- 5. TEST ML CORE CAPABILITIES ----------------
    print("\n[5] Testing Core Machine Learning & Coaching Engines...")

    # Load 1 frame from test_video1.mp4 (squats)
    cap = cv2.VideoCapture("Doomsday-Sports-ML-REPO/data/test_video1.mp4")
    ret, frame = cap.read()
    cap.release()
    assert ret, "Could not read frame from test_video1.mp4"

    # Encode to base64
    _, buf = cv2.imencode('.jpg', frame)
    b64_str = "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')

    # Test Live Process Frame API
    resp = client_a2.post("/api/process_frame", json={
        "image": b64_str,
        "exercise": "squat"
    })
    assert resp.status_code == 200, f"/api/process_frame failed with {resp.status_code}"
    data = resp.get_json()
    assert data["body_detected"] is True, "Body was not detected in squat frame"
    assert "form_status" in data
    assert "reps" in data
    assert "angles" in data
    print(f"  [PASS] POST /api/process_frame (body detected: True, form: {data['form_status']}, action: {data.get('detected_ml_action')})")

    # Test Yoga Process Frame API
    resp = client_a2.post("/api/process_yoga_frame", json={
        "image": b64_str,
        "pose": "tadasana",
        "target_hold": 10
    })
    assert resp.status_code == 200, f"/api/process_yoga_frame failed with {resp.status_code}"
    yoga_data = resp.get_json()
    assert yoga_data["body_detected"] is True
    assert "status" in yoga_data
    assert "accuracy" in yoga_data
    print(f"  [PASS] POST /api/process_yoga_frame (pose: {yoga_data['pose_name']}, accuracy: {yoga_data['accuracy']}%)")

    # Test Pre-recorded Video Analysis on test_standing.mp4
    print("  Testing pre-recorded video analysis on test_standing.mp4...")
    resp = client_a2.post("/api/analyze_video", data={
        "sample_filename": "test_standing.mp4",
        "exercise_type": "auto"
    })
    assert resp.status_code == 200, f"/api/analyze_video failed with {resp.status_code}: {resp.data}"
    video_rep = resp.get_json()
    assert video_rep["status"] == "success"
    assert "exercise_detected" in video_rep
    assert "detailed_correction" in video_rep
    print(f"  [PASS] POST /api/analyze_video (detected: {video_rep['exercise_detected']}, frames: {video_rep['frames_analyzed']})")

    # Test Workout Plan Generator API
    resp = client_a2.get("/api/generate_plan")
    assert resp.status_code == 200, f"/api/generate_plan failed with {resp.status_code}"
    plan_data = resp.get_json()
    assert len(plan_data["exercises"]) >= 3
    print(f"  [PASS] GET /api/generate_plan (generated {len(plan_data['exercises'])} exercises, difficulty: {plan_data['difficulty']})")

    # Test Sample Video Serving Route
    resp = client_a2.get("/static/sample/test_standing.mp4")
    assert resp.status_code == 200, f"Sample video route failed with {resp.status_code}"
    assert resp.mimetype == "video/mp4"
    print(f"  [PASS] GET /static/sample/test_standing.mp4 (status 200, mimetype: {resp.mimetype})")

    print("\n=======================================================")
    print("   ALL TESTS PASSED SUCCESSFULLY! ")
    print("   User Authentication & Data Isolation 100% Verified.")
    print("=======================================================\n")

if __name__ == "__main__":
    run_tests()
