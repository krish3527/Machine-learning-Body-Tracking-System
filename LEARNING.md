# LEARNING.md — What I learned building this project

## 1. Vector Math for Joint Angles

To measure the angle at a joint (e.g. knee), I need two vectors that both **originate at the joint**.

Given points A (hip), B (knee), C (ankle):
- `BA = A - B` → vector FROM knee TO hip
- `BC = C - B` → vector FROM knee TO ankle

Key insight: `endpoint - startpoint` gives a vector pointing from start → end. So to get a vector pointing *away* from B, subtract B from the other point — not the other way around.

## 2. Dot Product and Why It Encodes Angle

The geometric definition of dot product:

```
dot(BA, BC) = |BA| * |BC| * cos(θ)
```

Rearranging:

```
cos(θ) = dot(BA, BC) / (|BA| * |BC|)
θ = arccos(cos(θ))
```

The algebraic definition (`BA.x*BC.x + BA.y*BC.y`) computes the same number from coordinates. Both definitions are equivalent — the formula just rearranges the geometric definition to isolate θ.

Intuition for extreme cases:
- Same direction → dot product large positive → angle ≈ 0°
- Perpendicular → dot product = 0 → angle = 90°
- Opposite direction → dot product large negative → angle ≈ 180°

## 3. Why np.clip(-1, 1) is Necessary

`arccos` is only defined for values in `[-1, 1]`. Floating point arithmetic can produce values like `1.0000000002` due to rounding errors. Without clipping, this returns `nan` silently — a hard-to-debug bug. One line of defensive code prevents it.

## 4. Why Angles Are Better Features Than Raw Coordinates

Raw landmark coordinates (x, y) depend on:
- Person's distance from camera
- Person's height
- Camera angle

Angles are **scale-invariant and person-invariant**. A 90° knee bend looks the same regardless of body size or camera position. This is why 3 angles gave 98% accuracy with a simple classifier.

## 5. Random Forest vs SVM

SVM requires feature scaling (StandardScaler) because it's sensitive to the magnitude of input values. Random Forest is scale-invariant — it makes decisions based on thresholds, not distances. For a quick 3-feature classifier, RF needs less setup and gives `feature_importances_` for interpretability.

## 6. State Machine for Rep Counting

No ML needed for counting. A 2-state machine works:
- If angle > 160° → stage = "up"
- If angle < 90° AND stage was "up" → stage = "down", counter += 1

The `stage == "up"` check prevents double-counting — without it, every frame below 90° would increment the counter.

Thresholds must be calibrated empirically — print angles during exercise and observe the range. This is real engineering, not just code.

## 7. MediaPipe Pattern (same across all solutions)

The init pattern is identical whether using FaceMesh, Pose, or Hands:
1. `mp_X = mp.solutions.X`
2. `solution = mp_X.X(confidence params)`
3. Convert BGR → RGB before `solution.process(frame)`
4. Draw on BGR frame (not RGB) before saving/showing

BGR/RGB mismatch is a common silent bug — landmarks draw correctly but colors look wrong.
