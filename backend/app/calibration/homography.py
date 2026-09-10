"""
Workspace calibration: 4-point homography.

Converts camera pixel coordinates to normalized 2D workspace coordinates [0,1].
Clearly documents that this is an approximation (NOT true 3D reconstruction).
"""
import json
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from app.core.config import DATA_DIR


CALIBRATION_FILE = DATA_DIR / "calibration.json"


def compute_homography(src_points: List[Tuple[float, float]]) -> Optional[np.ndarray]:
    """
    Compute homography from 4 pixel points to unit square [0,1]x[0,1].
    src_points: 4 pixel coordinates (top-left, top-right, bottom-right, bottom-left)
    Returns 3x3 homography matrix or None if computation fails.
    """
    if len(src_points) < 4:
        return None
    src = np.array(src_points[:4], dtype=np.float32)
    dst = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)
    H, status = cv2_find_homography(src, dst)
    return H


def cv2_find_homography(src: np.ndarray, dst: np.ndarray):
    """Wrapper to avoid importing cv2 at module level."""
    import cv2
    return cv2.findHomography(src, dst)


def transform_point(H: np.ndarray, px: float, py: float) -> Optional[Tuple[float, float]]:
    """Transform a single pixel coordinate using homography."""
    if H is None:
        return None
    pt = np.array([[[px, py]]], dtype=np.float32)
    import cv2
    transformed = cv2.perspectiveTransform(pt, H)
    x, y = float(transformed[0][0][0]), float(transformed[0][0][1])
    # Clamp to [0,1]
    x = max(0.0, min(1.0, x))
    y = max(0.0, min(1.0, y))
    return (x, y)


def save_calibration(points: List[Tuple[float, float]], procedure_id: str,
                     frame_width: int, frame_height: int):
    """Persist calibration data to disk."""
    CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if CALIBRATION_FILE.exists():
        data = json.loads(CALIBRATION_FILE.read_text())
    data[procedure_id] = {
        "points": points,
        "frame_width": frame_width,
        "frame_height": frame_height,
    }
    CALIBRATION_FILE.write_text(json.dumps(data, indent=2))


def load_calibration(procedure_id: str) -> Optional[Dict]:
    """Load calibration for a procedure."""
    if not CALIBRATION_FILE.exists():
        return None
    data = json.loads(CALIBRATION_FILE.read_text())
    return data.get(procedure_id)


def get_homography_for_procedure(procedure_id: str) -> Optional[np.ndarray]:
    """Load and compute homography for a procedure."""
    cal = load_calibration(procedure_id)
    if cal is None:
        return None
    return compute_homography(cal["points"])
