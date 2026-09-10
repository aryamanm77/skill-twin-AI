"""
YOLO-based object detector.

Uses Ultralytics YOLO with ByteTrack for object detection and tracking.
In TEST MODE, returns synthetic detections matching the test camera frames.
"""
import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from app.core.config import settings, MODELS_DIR
from app.vision.camera import CameraMode


@dataclass
class Detection:
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]       # [x1, y1, x2, y2] normalized 0-1
    center: List[float]     # [cx, cy] normalized 0-1
    bbox_px: List[int]      # [x1, y1, x2, y2] in pixels
    center_px: List[int]    # [cx, cy] in pixels


@dataclass
class DetectionResult:
    detections: List[Detection]
    frame_timestamp: float
    inference_ms: float
    frame_width: int
    frame_height: int
    is_test_mode: bool
    model_status: str   # "ok", "missing", "loading", "error"


class YOLODetector:
    """Wraps Ultralytics YOLO with ByteTrack. Lazy-loads model."""

    def __init__(self):
        self._model = None
        self._model_status = "not_loaded"
        self._error: Optional[str] = None
        self._test_frame_count = 0

    def load(self) -> bool:
        """Attempt to load YOLO model. Returns True on success."""
        try:
            from ultralytics import YOLO
            model_path = MODELS_DIR / settings.YOLO_MODEL
            if not model_path.exists():
                # Download to models dir
                self._model_status = "downloading"
                import ultralytics
                m = YOLO(settings.YOLO_MODEL)  # will download to default location
                # move to our models dir
                import shutil, pathlib
                default_path = pathlib.Path(settings.YOLO_MODEL)
                if default_path.exists():
                    shutil.move(str(default_path), str(model_path))
                    m = YOLO(str(model_path))
                self._model = m
            else:
                self._model = YOLO(str(model_path))
            self._model_status = "ok"
            return True
        except Exception as e:
            self._error = str(e)
            self._model_status = "error"
            return False

    def detect(self, frame_image: np.ndarray, camera_mode: CameraMode) -> DetectionResult:
        """Run detection+tracking on a frame. Falls back to test mode if model absent."""
        t0 = time.perf_counter()
        h, w = frame_image.shape[:2]

        if camera_mode == CameraMode.TEST:
            dets = self._test_detections(w, h)
            return DetectionResult(
                detections=dets, frame_timestamp=time.time(),
                inference_ms=0.0, frame_width=w, frame_height=h,
                is_test_mode=True, model_status="test_mode"
            )

        if self._model is None:
            if not self.load():
                return DetectionResult(
                    detections=[], frame_timestamp=time.time(),
                    inference_ms=0.0, frame_width=w, frame_height=h,
                    is_test_mode=False,
                    model_status=f"error: {self._error or 'model not loaded'}"
                )

        try:
            results = self._model.track(
                frame_image,
                persist=True,
                tracker=settings.TRACKER_CONFIG,
                conf=settings.YOLO_CONFIDENCE,
                verbose=False,
            )
            dets = self._parse_results(results, w, h)
            inf_ms = (time.perf_counter() - t0) * 1000
            return DetectionResult(
                detections=dets, frame_timestamp=time.time(),
                inference_ms=inf_ms, frame_width=w, frame_height=h,
                is_test_mode=False, model_status="ok"
            )
        except Exception as e:
            return DetectionResult(
                detections=[], frame_timestamp=time.time(),
                inference_ms=0.0, frame_width=w, frame_height=h,
                is_test_mode=False, model_status=f"error: {e}"
            )

    def _parse_results(self, results, w: int, h: int) -> List[Detection]:
        dets = []
        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes
            for i in range(len(boxes)):
                try:
                    track_id = int(boxes.id[i]) if boxes.id is not None else -i
                    cls_id = int(boxes.cls[i])
                    cls_name = result.names[cls_id]
                    conf = float(boxes.conf[i])
                    x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i]]
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    dets.append(Detection(
                        track_id=track_id, class_id=cls_id, class_name=cls_name,
                        confidence=conf,
                        bbox=[x1/w, y1/h, x2/w, y2/h],
                        center=[cx/w, cy/h],
                        bbox_px=[int(x1), int(y1), int(x2), int(y2)],
                        center_px=[int(cx), int(cy)],
                    ))
                except Exception:
                    continue
        return dets

    def _test_detections(self, w: int, h: int) -> List[Detection]:
        """Synthetic detections that mimic the test camera's animated objects."""
        self._test_frame_count += 1
        t = time.time()
        synthetic = [
            (1, "bottle",   int(100 + 60*np.sin(t*0.5)),  int(500 + 30*np.cos(t*0.3)), 0.92),
            (2, "remote",   int(350 + 40*np.sin(t*0.4+1)),int(520 + 20*np.cos(t*0.6)), 0.87),
            (3, "book",     int(600 + 50*np.sin(t*0.3+2)),int(510 + 25*np.cos(t*0.4)), 0.83),
            (4, "scissors", int(900 + 30*np.sin(t*0.7)),  int(530 + 15*np.cos(t*0.5)), 0.89),
        ]
        dets = []
        for tid, name, cx, cy, conf in synthetic:
            x1, y1 = cx-30, cy-20
            x2, y2 = cx+30, cy+20
            dets.append(Detection(
                track_id=tid, class_id=0, class_name=name, confidence=conf,
                bbox=[x1/w, y1/h, x2/w, y2/h],
                center=[cx/w, cy/h],
                bbox_px=[x1, y1, x2, y2],
                center_px=[cx, cy],
            ))
        return dets

    @property
    def model_status(self) -> str:
        return self._model_status

    @property
    def error(self) -> Optional[str]:
        return self._error


# ── Singleton ──────────────────────────────────────────────────────────────────
_detector_instance: Optional[YOLODetector] = None


def get_detector() -> YOLODetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = YOLODetector()
    return _detector_instance
