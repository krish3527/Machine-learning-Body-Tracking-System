"""
core/action_classifier.py
Wrapper around the existing pretrained Random Forest action classifier model.
Loads the model from data/action_model.pkl and predicts action classes (squat, pushup, standing).
Reuses angle calculation from angle_utils.py.
"""

import os
import sys
import pickle
import warnings
import numpy as np

# Suppress unpickling version warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Resolve path to angle_utils.py from the existing repo
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
    # Safe fallback if angle_utils is directly imported
    def calculate_angle(a, b, c):
        BA = np.array(a) - np.array(b)
        BC = np.array(c) - np.array(b)
        dot = np.dot(BA, BC)
        mag = np.linalg.norm(BA) * np.linalg.norm(BC)
        if mag == 0:
            return 0.0
        cos_angle = dot / mag
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_angle)))


class ActionClassifier:
    def __init__(self, model_path=None):
        self.model = None
        self.classes = []
        self.model_path = model_path or self._find_model_path()
        self._load_model()

    def _find_model_path(self):
        candidates = [
            os.path.join(_PROJECT_ROOT, "Doomsday-Sports-ML-REPO", "data", "action_model.pkl"),
            os.path.join(_PROJECT_ROOT, "data", "action_model.pkl"),
            os.path.join("Doomsday-Sports-ML-REPO", "data", "action_model.pkl"),
            os.path.join("data", "action_model.pkl"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return candidates[0]

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print(f"[ActionClassifier] Model file not found at {self.model_path}")
            return
        try:
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)
            self.classes = list(getattr(self.model, "classes_", ["pushup", "squat", "standing"]))
            print(f"[ActionClassifier] Successfully loaded model from {self.model_path} with classes {self.classes}")
        except Exception as e:
            print(f"[ActionClassifier] Error loading model: {e}")

    def predict(self, knee_angle: float, elbow_angle: float, hip_angle: float):
        """
        Predicts action using the exact 3 features expected by the trained Random Forest model:
        [knee_angle, elbow_angle, hip_angle].
        Returns:
            label (str): 'squat', 'pushup', or 'standing'
            confidence (float): prediction probability (0.0 to 1.0)
            probabilities (dict): mapping of class name to probability
        """
        if self.model is None:
            # Fallback heuristic if model is not loaded
            if knee_angle < 120 and hip_angle < 130:
                return "squat", 0.85, {"squat": 0.85, "pushup": 0.1, "standing": 0.05}
            elif elbow_angle < 110:
                return "pushup", 0.85, {"pushup": 0.85, "squat": 0.1, "standing": 0.05}
            return "standing", 0.90, {"standing": 0.90, "squat": 0.05, "pushup": 0.05}

        features = np.array([[float(knee_angle), float(elbow_angle), float(hip_angle)]])
        try:
            label = self.model.predict(features)[0]
            probs = {}
            if hasattr(self.model, "predict_proba"):
                prob_vals = self.model.predict_proba(features)[0]
                probs = {cls_name: float(p) for cls_name, p in zip(self.model.classes_, prob_vals)}
                confidence = float(max(prob_vals))
            else:
                confidence = 1.0
                probs = {label: 1.0}
            return str(label), confidence, probs
        except Exception as e:
            print(f"[ActionClassifier] Prediction error: {e}")
            return "unknown", 0.0, {}
