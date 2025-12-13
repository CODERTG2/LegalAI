import numpy as np

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    return 1-(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))