# angle_utils.py
# calculates the angle here
import numpy as np

def calculate_angle(a, b, c):
    """
    Calculate angle at joint b.
    a, b, c → [x, y] or [x, y, z] coords (lists or numpy arrays)
    returns angle in degrees
    dot(BA, BC) = |BA| * |BC| * cos(θ)
    """
    BA = np.array(a) - np.array(b)
    BC = np.array(c) - np.array(b) 

    dot = np.dot(BA, BC)
    mag = np.linalg.norm(BA) * np.linalg.norm(BC)

    cos_angle = dot / mag 
    cos_angle = np.clip(cos_angle, -1, 1)
    angle = np.degrees(np.arccos(cos_angle))
    return angle