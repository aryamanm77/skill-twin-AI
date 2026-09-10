"""
Camera input abstraction.

Supports:
  - REAL: live webcam (OpenCV VideoCapture)
  - VIDEO: MP4/AVI file upload
  - TEST: synthetic frame generator (clearly labelled)
"""
import time
import threading
import queue
import numpy as np
import cv2
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple
from app.core.config import settings


class CameraMode(str, Enum):
    REAL = "real"
    VIDEO = "video"
    TEST = "test"


@dataclass
class Frame:
    image: np.ndarray
    timestamp: float
    frame_number: int
    mode: CameraMode
    width: int
    height: int


class CameraError(Exception):
    pass


class CameraSource:
    """Thread-safe camera that maintains a queue of recent frames."""

    def __init__(self, mode: CameraMode = CameraMode.TEST,
                 source: Optional[str] = None):
        self.mode = mode
        self.source = source
        self._cap: Optional[cv2.VideoCapture] = None
        self._queue: queue.Queue = queue.Queue(maxsize=4)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._error: Optional[str] = None
        self._lock = threading.Lock()

    # ── Public API ─────────────────────────────────────────────────────────────
    def start(self):
        if self._running:
            return
        if self.mode == CameraMode.REAL:
            self._open_webcam()
        elif self.mode == CameraMode.VIDEO:
            self._open_video()
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap and self._cap.isOpened():
            self._cap.release()

    def get_frame(self, timeout: float = 0.1) -> Optional[Frame]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def error(self) -> Optional[str]:
        return self._error

    def get_status(self) -> dict:
        return {
            "mode": self.mode.value,
            "running": self._running,
            "error": self._error,
            "frame_count": self._frame_count,
        }

    # ── Private ────────────────────────────────────────────────────────────────
    def _open_webcam(self):
        idx = int(self.source) if self.source and self.source.isdigit() else settings.CAMERA_INDEX
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            # Try without backend hint
            cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            self._error = f"Cannot open webcam index {idx}. Check camera connection."
            raise CameraError(self._error)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, settings.CAMERA_FPS)
        self._cap = cap

    def _open_video(self):
        if not self.source:
            self._error = "Video source path required."
            raise CameraError(self._error)
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self._error = f"Cannot open video file: {self.source}"
            raise CameraError(self._error)
        self._cap = cap

    def _capture_loop(self):
        while self._running:
            try:
                frame = self._generate_frame()
                if frame is None:
                    time.sleep(0.033)
                    continue
                # Drop oldest if queue full
                if self._queue.full():
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                self._queue.put(frame)
                self._frame_count += 1
            except Exception as e:
                self._error = str(e)
                time.sleep(0.1)

    def _generate_frame(self) -> Optional[Frame]:
        if self.mode == CameraMode.TEST:
            return self._generate_test_frame()
        elif self._cap and self._cap.isOpened():
            ret, img = self._cap.read()
            if not ret:
                if self.mode == CameraMode.VIDEO:
                    # Loop video
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, img = self._cap.read()
                if not ret:
                    self._error = "Failed to read frame from camera"
                    return None
            h, w = img.shape[:2]
            return Frame(image=img, timestamp=time.time(),
                         frame_number=self._frame_count, mode=self.mode,
                         width=w, height=h)
        return None

    def _generate_test_frame(self) -> Frame:
        """Generate a synthetic test frame with moving objects. CLEARLY LABELLED."""
        t = time.time()
        w, h = 1280, 720
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (15, 20, 30)  # dark background

        # Animated objects
        objs = [
            ("Component A", (int(100 + 60 * np.sin(t * 0.5)), int(500 + 30 * np.cos(t * 0.3))), (70, 130, 220)),
            ("Component B", (int(350 + 40 * np.sin(t * 0.4 + 1)), int(520 + 20 * np.cos(t * 0.6))), (140, 80, 210)),
            ("Component C", (int(600 + 50 * np.sin(t * 0.3 + 2)), int(510 + 25 * np.cos(t * 0.4))), (200, 60, 130)),
            ("Tool",        (int(900 + 30 * np.sin(t * 0.7)), int(530 + 15 * np.cos(t * 0.5))), (40, 180, 160)),
        ]
        for name, (cx, cy), color in objs:
            cv2.rectangle(img, (cx-30, cy-20), (cx+30, cy+20), color, 2)
            cv2.putText(img, name, (cx-28, cy-25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Assembly zone
        cv2.rectangle(img, (384, 72), (896, 360), (30, 180, 80), 2)
        cv2.putText(img, "ASSEMBLY ZONE", (390, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 180, 80), 1)

        # TEST MODE watermark
        cv2.putText(img, "⚠ SIMULATION / TEST MODE - NOT REAL CAMERA", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
        cv2.putText(img, f"Synthetic frame #{self._frame_count}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        time.sleep(1 / 30.0)
        return Frame(image=img, timestamp=t, frame_number=self._frame_count,
                     mode=CameraMode.TEST, width=w, height=h)


# ── Singleton camera instance ──────────────────────────────────────────────────
_camera_instance: Optional[CameraSource] = None


def get_camera(mode: CameraMode = CameraMode.TEST,
               source: Optional[str] = None) -> CameraSource:
    global _camera_instance
    if _camera_instance is None or not _camera_instance.is_running:
        if _camera_instance:
            _camera_instance.stop()
        _camera_instance = CameraSource(mode=mode, source=source)
    return _camera_instance


def restart_camera(mode: CameraMode = CameraMode.TEST,
                   source: Optional[str] = None) -> CameraSource:
    global _camera_instance
    if _camera_instance:
        _camera_instance.stop()
    _camera_instance = CameraSource(mode=mode, source=source)
    return _camera_instance
