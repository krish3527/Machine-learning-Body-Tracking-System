"""
run.py
Launcher script for ApexMotion
Runs pre-flight checks and starts the Flask web application.
"""

import sys
import os

def check_environment():
    print("Checking dependencies...")
    required_packages = ["mediapipe", "cv2", "sklearn", "flask", "numpy"]
    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Error: Missing required packages: {', '.join(missing)}")
        print("Please install them using: pip install -r requirements.txt")
        sys.exit(1)
    print("All core dependencies verified successfully.")

if __name__ == "__main__":
    check_environment()
    from app import app
    print("\n=======================================================")
    print("   ApexMotion - Smart Fitness Coaching System")
    print("   Local Server: http://127.0.0.1:5000")
    print("   Open the above URL in your browser to start.")
    print("=======================================================\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
