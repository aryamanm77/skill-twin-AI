"""
Object tracker: maintains object history, trajectory, and zone membership.
Wraps detector output into TrackedObject with temporal context.
"""
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Deque
from app.vision.detector import Detection


MAX_HISTORY = 300       # max positions per object
MISSING_TIMEOUT = 3.0   # seconds before object considered lost


@dataclass
class TrackedObject:
    track_id: int
    class_name: str
    confidence: float
    center: List[float]         # normalized [cx, cy]
    center_px: List[int]
    bbox: List[float]           # normalized
    workspace_pos: Optional[List[float]]  # calibrated 2D position
    history: List[Dict]         # [{ts, cx, cy, ws_x, ws_y}]
    last_seen: float
    first_seen: float
    is_active: bool
    current_zones: List[str]    # zone IDs where object currently resides
    frames_seen: int


class ObjectTracker:
    """
    Maintains per-ID state and trajectory history.
    Handles temporary disappearances gracefully.
    """

    def __init__(self):
        self._objects: Dict[int, TrackedObject] = {}
        self._zone_checker = None  # injected after calibration

    def set_zone_checker(self, checker):
        """Inject a zone checker (from calibration module)."""
        self._zone_checker = checker

    def update(self, detections: List[Detection],
               homography=None) -> List[TrackedObject]:
        """Update tracker with new detections. Returns active tracked objects."""
        now = time.time()
        seen_ids = set()

        for det in detections:
            tid = det.track_id
            seen_ids.add(tid)

            # Workspace position via homography
            ws_pos = None
            if homography is not None:
                import numpy as np
                from app.calibration.homography import transform_point
                ws_pos = transform_point(homography, det.center_px[0], det.center_px[1])

            # Zone membership
            zones = []
            if self._zone_checker is not None:
                zones = self._zone_checker(det.center[0], det.center[1])

            hist_entry = {
                "ts": now,
                "cx": det.center[0], "cy": det.center[1],
                "cx_px": det.center_px[0], "cy_px": det.center_px[1],
                "ws_x": ws_pos[0] if ws_pos else None,
                "ws_y": ws_pos[1] if ws_pos else None,
                "zones": zones,
            }

            if tid in self._objects:
                obj = self._objects[tid]
                obj.class_name = det.class_name
                obj.confidence = det.confidence
                obj.center = det.center
                obj.center_px = det.center_px
                obj.bbox = det.bbox
                obj.workspace_pos = ws_pos
                obj.last_seen = now
                obj.is_active = True
                obj.current_zones = zones
                obj.frames_seen += 1
                obj.history.append(hist_entry)
                if len(obj.history) > MAX_HISTORY:
                    obj.history.pop(0)
            else:
                self._objects[tid] = TrackedObject(
                    track_id=tid, class_name=det.class_name,
                    confidence=det.confidence,
                    center=det.center, center_px=det.center_px,
                    bbox=det.bbox, workspace_pos=ws_pos,
                    history=[hist_entry],
                    last_seen=now, first_seen=now,
                    is_active=True, current_zones=zones, frames_seen=1,
                )

        # Mark missing objects
        for tid, obj in self._objects.items():
            if tid not in seen_ids:
                if now - obj.last_seen > MISSING_TIMEOUT:
                    obj.is_active = False

        return [o for o in self._objects.values() if o.is_active]

    def get_object(self, track_id: int) -> Optional[TrackedObject]:
        return self._objects.get(track_id)

    def get_all_active(self) -> List[TrackedObject]:
        return [o for o in self._objects.values() if o.is_active]

    def get_trajectory(self, track_id: int) -> List[Dict]:
        obj = self._objects.get(track_id)
        return obj.history if obj else []

    def get_path_length_normalized(self, track_id: int) -> float:
        """Path length in normalized workspace units."""
        obj = self._objects.get(track_id)
        if not obj or len(obj.history) < 2:
            return 0.0
        total = 0.0
        pts = [(h["cx"], h["cy"]) for h in obj.history]
        for i in range(1, len(pts)):
            dx = pts[i][0] - pts[i-1][0]
            dy = pts[i][1] - pts[i-1][1]
            total += (dx**2 + dy**2) ** 0.5
        return total

    def reset(self):
        self._objects.clear()

    def snapshot(self) -> List[Dict]:
        """Serializable snapshot of all active objects."""
        result = []
        for obj in self._objects.values():
            result.append({
                "track_id": obj.track_id,
                "class_name": obj.class_name,
                "confidence": obj.confidence,
                "center": obj.center,
                "center_px": obj.center_px,
                "workspace_pos": obj.workspace_pos,
                "current_zones": obj.current_zones,
                "is_active": obj.is_active,
                "frames_seen": obj.frames_seen,
                "path_length": self.get_path_length_normalized(obj.track_id),
            })
        return result


# ── Singleton ──────────────────────────────────────────────────────────────────
_tracker_instance: Optional[ObjectTracker] = None


def get_tracker() -> ObjectTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ObjectTracker()
    return _tracker_instance
