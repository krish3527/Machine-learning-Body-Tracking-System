# pose_detector.py

import cv2
import mediapipe as mp
from angle_utils import calculate_angle
import csv
import pickle


# 1. init mediapipe pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 2. open video
cap = cv2.VideoCapture("data/test_pushup.mp4")
# before while loop — add this after cap = cv2.VideoCapture(...)
width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps    = int(cap.get(cv2.CAP_PROP_FPS))
out = cv2.VideoWriter("data/output.mp4", cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

csv_file = open("data/training_data.csv", "a", newline="")
writer = csv.writer(csv_file)
writer.writerow(["knee_angle", "elbow_angle", "hip_angle", "label"])

with open("data/action_model.pkl", "rb") as f:
    model = pickle.load(f)

counter = 0
stage = None

# 3. loop frames
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    # 4. convert BGR → RGB (mediapipe needs RGB)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # 5. process frame
    results = pose.process(rgb)
    
    # 6. extract landmarks if detected
    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        
        # get hip, knee, ankle coords as [x, y]
        hip   = [landmarks[23].x, landmarks[23].y]
        knee  = [landmarks[25].x, landmarks[25].y]
        ankle = [landmarks[27].x, landmarks[27].y]
        shoulder = [landmarks[11].x, landmarks[11].y]
        elbow = [landmarks[13].x, landmarks[13].y]
        wrist = [landmarks[15].x, landmarks[15].y]
        
        # calculate angle
        angle = calculate_angle(shoulder, elbow, wrist)
        
        # print angle
        print(angle)
        if angle > 160:
            stage = "up"
        if angle < 90 and stage == "up":
            stage = "down"
            counter += 1
            print(f"Rep: {counter}")
        
        # draw landmarks on frame
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        cv2.putText(frame, f"Reps: {counter}", (10, 50), 
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv2.putText(frame, f"Angle: {int(angle)}", (10, 100), 
            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # inside loop after calculating angles
        knee_angle  = calculate_angle(hip, knee, ankle)
        elbow_angle = calculate_angle(shoulder, elbow, wrist)
        hip_angle   = calculate_angle(shoulder, hip, knee)
        
        features = [[knee_angle, elbow_angle, hip_angle]]
        action = model.predict(features)[0]

        label = "standing"  # change per video

        writer.writerow([knee_angle, elbow_angle, hip_angle, label])
        cv2.putText(frame, f"Action: {action}", (width - 250, 50),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)

    out.write(frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

out.release()
cap.release()
cv2.destroyAllWindows()