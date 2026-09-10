"""
Core vision pipeline: runs continuously in a background thread,
feeding frames through YOLO → tracker → FSM → WebSocket broadcast.
"""
import asyncio
import base64
import threading
import time
import uuid
import numpy as np
import cv2
from typing import Optional, Dict, Any, List
from app.vision.camera import CameraSource, CameraMode, Frame
from app.vision.detector import get_detector, DetectionResult
from app.tracking.tracker import get_tracker, ObjectTracker, TrackedObject
from app.procedure_engine.loader import ProcedureConfig, parse_procedure
from app.procedure_engine.fsm import ProcedureFSM, StepRecord
from app.procedure_engine.comparator import compare
from app.scoring.scorer import compute_score, score_to_dict
from app.api.ws_manager import manager, WSMessage
from app.calibration.zones import zones_from_procedure
from app.calibration.homography import get_homography_for_procedure
from app.core.config import settings


class VisionPipeline:
    """
    Orchestrates: Camera → YOLO → Tracker → FSM → Scoring → WebSocket.
    Thread-safe, async-broadcast capable.
    """

    def __init__(self):
        self._camera: Optional[CameraSource] = None
        self._procedure: Optional[ProcedureConfig] = None
        self._fsm: Optional[ProcedureFSM] = None
        self._tracker: ObjectTracker = get_tracker()
        self._detector = get_detector()
        self._mode: str = "idle"     # idle, expert, trainee, test
        self._session_id: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._homography = None
        self._zone_checker = None
        self._expert_steps: Optional[List[Dict]] = None  # reference for trainee mode
        self._current_score: Optional[Dict] = None
        self._trajectory_data: Dict[int, List] = {}
        self._frame_count = 0
        self._last_frame_data: Optional[Dict] = None
        self._lock = threading.Lock()

    # ── Session Control ────────────────────────────────────────────────────────
    def start_session(self, session_id: str, procedure_config: dict,
                      mode: str, camera: CameraSource,
                      expert_steps: Optional[List[Dict]] = None,
                      event_loop: Optional[asyncio.AbstractEventLoop] = None):
        with self._lock:
            if self._running:
                self.stop_session()

            self._session_id = session_id
            self._procedure = parse_procedure(procedure_config)
            self._mode = mode
            self._camera = camera
            self._expert_steps = expert_steps
            self._loop = event_loop
            self._tracker.reset()
            self._fsm = ProcedureFSM(self._procedure)
            self._current_score = None
            self._trajectory_data = {}
            self._frame_count = 0

            # Setup zones and calibration
            self._zone_checker = zones_from_procedure(procedure_config)
            self._homography = get_homography_for_procedure(self._procedure.id)
            self._tracker.set_zone_checker(
                lambda nx, ny: self._zone_checker.check(nx, ny)
            )

            if not self._camera.is_running:
                self._camera.start()

            self._running = True
            self._thread = threading.Thread(target=self._pipeline_loop, daemon=True)
            self._thread.start()

    def stop_session(self) -> Optional[Dict]:
        """Stop session and return final results."""
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

        result = None
        if self._fsm and self._mode == "trainee" and self._expert_steps:
            records = self._fsm.finish_session()
            comparison = compare(self._procedure, self._expert_steps, records)
            score = compute_score(self._procedure, comparison)
            result = {
                "session_id": self._session_id,
                "score": score_to_dict(score),
                "step_records": [self._fsm._record_to_dict(r) for r in records],
                "trajectory_data": {str(k): v for k, v in self._trajectory_data.items()},
                "events": [self._event_to_dict(e) for e in self._fsm.events],
            }
        elif self._fsm and self._mode == "expert":
            records = self._fsm.finish_session()
            result = {
                "session_id": self._session_id,
                "step_records": [self._fsm._record_to_dict(r) for r in records],
                "trajectory_data": {str(k): v for k, v in self._trajectory_data.items()},
                "events": [self._event_to_dict(e) for e in self._fsm.events],
                "total_duration_s": time.time() - (self._fsm.session_start_time or time.time()),
            }
        return result

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def mode(self) -> str:
        return self._mode

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "mode": self._mode,
            "session_id": self._session_id,
            "frame_count": self._frame_count,
            "camera": self._camera.get_status() if self._camera else {"running": False},
            "model_status": self._detector.model_status,
            "fsm_state": self._fsm.get_snapshot() if self._fsm else None,
            "current_score": self._current_score,
        }

    # ── Pipeline loop (runs in thread) ─────────────────────────────────────────
    def _pipeline_loop(self):
        while self._running:
            try:
                frame = self._camera.get_frame(timeout=0.1)
                if frame is None:
                    continue

                # YOLO detection + tracking
                det_result = self._detector.detect(frame.image, frame.mode)

                # Update tracker
                tracked = self._tracker.update(
                    det_result.detections,
                    homography=self._homography,
                )

                # Update trajectory data
                for obj in tracked:
                    if obj.track_id not in self._trajectory_data:
                        self._trajectory_data[obj.track_id] = []
                    self._trajectory_data[obj.track_id] = obj.history[-100:]

                # FSM update → new events
                fsm_events = []
                if self._fsm:
                    fsm_events = self._fsm.update(tracked)

                # Compute live score in trainee mode
                if self._mode == "trainee" and self._expert_steps and self._fsm:
                    records = self._fsm.step_records
                    if records:
                        try:
                            comp = compare(self._procedure, self._expert_steps, records)
                            score = compute_score(self._procedure, comp)
                            self._current_score = score_to_dict(score)
                        except Exception:
                            pass

                # Encode frame for streaming
                jpeg_b64 = self._encode_frame(frame, det_result, tracked)

                self._frame_count += 1

                # Broadcast over WebSocket (fire-and-forget from thread)
                if self._loop and manager.connected_count > 0:
                    self._broadcast_async({
                        "frame": jpeg_b64,
                        "tracked": self._tracker.snapshot(),
                        "fsm": self._fsm.get_snapshot() if self._fsm else None,
                        "score": self._current_score,
                        "fsm_events": [self._event_to_dict(e) for e in fsm_events],
                        "model_status": det_result.model_status,
                        "inference_ms": det_result.inference_ms,
                        "test_mode": det_result.is_test_mode,
                    })

            except Exception as e:
                if self._loop:
                    asyncio.run_coroutine_threadsafe(
                        manager.broadcast(WSMessage.error(str(e))), self._loop
                    )
                time.sleep(0.05)

    def _encode_frame(self, frame: "Frame", det_result: DetectionResult,
                       tracked: List[TrackedObject]) -> str:
        """Draw detections on frame and JPEG encode to base64."""
        img = frame.image.copy()
        h, w = img.shape[:2]

        for obj in tracked:
            bp = obj.bbox_px if hasattr(obj, 'bbox_px') else None
            # Draw from detection result
            for det in det_result.detections:
                if det.track_id == obj.track_id:
                    x1, y1, x2, y2 = det.bbox_px
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 200, 100), 2)
                    label = f"[{det.track_id}] {det.class_name} {det.confidence:.2f}"
                    cv2.putText(img, label, (x1, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 100), 1)
                    # Zone label
                    if obj.current_zones:
                        zone_str = ",".join(obj.current_zones[:1])
                        cv2.putText(img, zone_str, (x1, y2+14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 200, 255), 1)

        # Mode watermark
        if det_result.is_test_mode:
            cv2.putText(img, "⚠ SIMULATION / TEST MODE", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)

        # Mode label
        mode_color = (0, 200, 100) if self._mode == "expert" else (255, 160, 0)
        cv2.putText(img, f"MODE: {self._mode.upper()}", (w-200, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, mode_color, 2)

        # Current step
        if self._fsm and self._fsm.current_step:
            step = self._fsm.current_step
            cv2.putText(img, f"STEP {step.order}: {step.name}", (10, h-15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 100), 1)

        # JPEG encode
        ret, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ret:
            return base64.b64encode(buf.tobytes()).decode("utf-8")
        return ""

    def _broadcast_async(self, data: Dict):
        """Thread-safe async broadcast."""
        if not self._loop:
            return
        msg = {
            "type": "pipeline_update",
            "timestamp": time.time(),
            "data": data,
        }
        asyncio.run_coroutine_threadsafe(manager.broadcast(msg), self._loop)

    @staticmethod
    def _event_to_dict(e) -> Dict:
        return {
            "event_type": e.event_type, "timestamp": e.timestamp,
            "step_id": e.step_id, "step_name": e.step_name,
            "detected_object": e.detected_object, "expected_object": e.expected_object,
            "message": e.message, "severity": e.severity, "data": e.data,
        }


# ── Singleton pipeline ─────────────────────────────────────────────────────────
_pipeline_instance: Optional[VisionPipeline] = None


def get_pipeline() -> VisionPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = VisionPipeline()
    return _pipeline_instance
