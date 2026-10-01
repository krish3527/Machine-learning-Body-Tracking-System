# Human Pose Estimation + Action Recognition

Real-time action classification (squat / pushup / standing) using joint angle geometry and a Random Forest classifier — no deep learning required for the classification layer.

## Demo

![Demo](demo/demo.gif)

## Architecture

```
Video Frame
    │
    ▼
MediaPipe Pose ──► 33 Body Landmarks
    │
    ▼
Joint Angle Extraction
  ├── Knee Angle  (Hip → Knee → Ankle)
  ├── Elbow Angle (Shoulder → Elbow → Wrist)
  └── Hip Angle   (Shoulder → Hip → Knee)
    │
    ▼
Random Forest Classifier
    │
    ▼
Action Label + Rep Counter

```

## Results

| Action | Precision | Recall | F1 |
|--------|-----------|--------|----|
| Pushup | 0.99 | 0.99 | 0.99 |
| Squat | 0.96 | 0.99 | 0.97 |
| Standing | 1.00 | 0.89 | 0.94 |
| **Overall** | **0.98** | **0.98** | **0.98** |

## Tech Stack

- Python 3.10+
- MediaPipe 0.10.13
- OpenCV 4.9
- scikit-learn 1.4
- NumPy 1.26

## Installation

```bash
# System dependency (Linux)
sudo apt-get install -y libgl1

# Python dependencies
pip install -r requirements.txt
```

## Usage

**1. Run pose detection + data collection:**
```bash
python src/pose_detector.py
# Output saved to data/output.mp4
# Training data saved to data/training_data.csv
```

**2. Train classifier:**
```bash
python src/action_classifier.py
# Model saved to data/action_model.pkl
```

## Project Structure

```
pose-action-recognition/
├── src/
│   ├── angle_utils.py        # Joint angle math (dot product formula)
│   ├── pose_detector.py      # MediaPipe pose + rep counter + prediction
│   └── action_classifier.py  # RandomForest training + evaluation
├── notebooks/
│   └── experiments.ipynb
├── data/
│   ├── training_data.csv     # Labeled angle features
│   └── action_model.pkl      # Trained classifier
├── demo/
│   └── demo_clip.mp4
├── requirements.txt
├── LEARNING.md
└── README.md
```

## Key Design Decisions

**Why 3 angles instead of raw landmarks?**
Raw x,y coordinates vary by person height, camera distance, and body position. Angles are scale-invariant — a squat looks like a squat regardless of how far you stand from the camera.

**Why Random Forest over SVM?**
Random Forest requires no feature scaling. SVM needs `StandardScaler` first or angles on different scales hurt performance. RF also gives `feature_importances_` for free.

**Why a state machine for rep counting?**
Simple and interpretable. No ML needed — just track when angle crosses thresholds in the right sequence: above 160° (up) → below 90° (down) → count.

## Failure Cases

- Standing frames sometimes misclassified as squat — knee angles overlap at the top of squat position. More standing training data would fix this.
- Low-light or partially occluded body reduces MediaPipe landmark confidence — handle with `visibility` score threshold.

## What I Learned

See [LEARNING.md](LEARNING.md)
