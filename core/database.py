"""
core/database.py
ApexMotion User Authentication & Workout Storage Layer.
Provides SQLite database persistence with secure password hashing (Werkzeug),
user isolation, and workout logging.
"""

import os
import sqlite3
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apexmotion.db")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Creates a database connection with dict-like row access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DB_PATH):
    """Initializes tables for users and user-isolated workout logs."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Workouts Table (Strictly isolated by user_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise TEXT NOT NULL,
            reps TEXT NOT NULL,
            duration TEXT NOT NULL,
            form_status TEXT NOT NULL DEFAULT 'Good',
            detected_issues TEXT DEFAULT '',
            feedback TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    """)

    # Indices for high performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_user ON workouts(user_id);")

    conn.commit()
    conn.close()


def validate_email(email: str) -> bool:
    """Validates email format."""
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email.strip()))


def create_user(name: str, email: str, password: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Creates a new user with hashed password.
    Raises ValueError on invalid input or existing email.
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()

    if not name:
        raise ValueError("Name cannot be empty.")
    if not validate_email(email):
        raise ValueError("Please enter a valid email address.")
    if not password or len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")

    password_hash = generate_password_hash(password)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("An account with this email already exists.")
    
    conn.close()
    return {"id": user_id, "name": name, "email": email}


def authenticate_user(email: str, password: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """
    Authenticates a user against hashed password.
    Returns user dict without password hash if valid, otherwise None.
    """
    email = (email or "").strip().lower()
    if not email or not password:
        return None

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    return None


def get_user_by_id(user_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves user public profile by ID."""
    if not user_id:
        return None
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None


def get_user_by_email(email: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves user public profile by email."""
    if not email:
        return None
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, created_at FROM users WHERE email = ?", (email.strip().lower(),))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None


# ---------------- USER-SPECIFIC WORKOUT OPERATIONS ----------------

def add_workout(
    user_id: int,
    exercise: str,
    reps: Any,
    duration: str,
    form_status: str = "Good",
    detected_issues: str = "",
    feedback: str = "",
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """Adds a workout record strictly tied to user_id."""
    if not user_id:
        raise ValueError("User ID is required to save workout.")

    reps_str = str(reps).strip() if reps is not None else "0"
    duration_str = str(duration).strip() if duration else "00:00"
    form_str = str(form_status).strip() if form_status else "Good"

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workouts (user_id, exercise, reps, duration, form_status, detected_issues, feedback)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        exercise,
        reps_str,
        duration_str,
        form_str,
        detected_issues or "",
        feedback or ""
    ))
    workout_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row)


def get_user_workouts(user_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Returns workout records belonging ONLY to user_id.
    Ordered by newest first.
    """
    if not user_id:
        return []

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, exercise, reps, duration, form_status, detected_issues, feedback, created_at
        FROM workouts
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_workout(user_id: int, workout_id: int, db_path: str = DB_PATH) -> bool:
    """
    Deletes a workout record ONLY if it belongs to user_id.
    Guarantees cross-user data safety.
    """
    if not user_id or not workout_id:
        return False

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM workouts WHERE id = ? AND user_id = ?", (workout_id, user_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def clear_user_workouts(user_id: int, db_path: str = DB_PATH) -> int:
    """
    Clears all workouts belonging ONLY to user_id.
    Leaves other users' data completely intact.
    """
    if not user_id:
        return 0

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM workouts WHERE user_id = ?", (user_id,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def seed_test_accounts(db_path: str = DB_PATH):
    """
    Seeds test accounts test1@example.com and test2@example.com
    with isolated workout data for automated testing and demonstrations.
    """
    init_db(db_path)

    # 1. Test User A
    user_a = get_user_by_email("test1@example.com", db_path)
    if not user_a:
        user_a = create_user("Test Athlete A", "test1@example.com", "test1234", db_path)
        # Workouts for User A
        add_workout(user_a["id"], "Squat", "20", "04:32", "Good", "", "Kept upright spine and reached parallel depth.", db_path)
        add_workout(user_a["id"], "Push-up", "15", "02:45", "Good", "", "Maintained straight plank alignment.", db_path)
        add_workout(user_a["id"], "Tree Pose", "1 hold", "01:00", "Good", "", "Stable posture balance maintained.", db_path)

    # 2. Test User B
    user_b = get_user_by_email("test2@example.com", db_path)
    if not user_b:
        user_b = create_user("Test Athlete B", "test2@example.com", "test1234", db_path)
        # Workouts for User B
        add_workout(user_b["id"], "Squat", "10", "02:10", "Needs Improvement", "Forward torso lean", "Focus on upright chest during descent.", db_path)
        add_workout(user_b["id"], "Push-up", "8", "01:30", "Good", "", "Smooth movement tempo.", db_path)

