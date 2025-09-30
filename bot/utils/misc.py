from math import sqrt

def scale_norm(k: float, w: float, h: float) -> float:
    return k * sqrt(w * h)