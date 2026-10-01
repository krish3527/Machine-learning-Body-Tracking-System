# sklearn model later we will implement here
# action classifier 
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pickle

# 1. load data
df = pd.read_csv("data/training_data.csv")

# 2. split features and label
X = df[['knee_angle', 'elbow_angle', 'hip_angle']]  # 3 angle columns
y = df['label']  # label column

# 3. train test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. train
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. evaluate
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# 6. save model
with open("data/action_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("Model saved.")