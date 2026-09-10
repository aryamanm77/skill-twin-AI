"""
Finite State Machine for procedure step recognition.

Logic: zone-based temporal state transitions driven by object tracking.
All transitions are explicit and logged — NOT a black-box ML model.

Action inference rules:
  PICK:     Object was in source_zone, now absent (moved with person)
  MOVE:     Object's center is moving significantly toward target_zone
  PLACE:    Object appeared in target_zone and stopped moving
  TOOL_USE: Tool enters assembly/target zone and stays there
  COMPLETE: All required steps done
"""
import time
import math
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from app.procedure_engine.loader import ProcedureConfig, ProcedureStep, get_object_by_yolo_class
from app.tracking.tracker import TrackedObject


class StepState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class StepRecord:
    step_id: str
    step_name: str
    expected_object: Optional[str]
    detected_object: Optional[str]
    state: StepState
    started_at: Optional[float]
    completed_at: Optional[float]
    duration_s: Optional[float]
    position_at_completion: Optional[List[float]]
    trajectory_snapshot: List[Dict]   # history of object positions during step
    sequence_order: int               # actual order detected
    notes: str = ""


@dataclass
class FSMEvent:
    """Emitted when something meaningful happens."""
    event_type: str   # step_started, step_completed, step_failed, wrong_object, sequence_deviation
    timestamp: float
    step_id: Optional[str]
    step_name: Optional[str]
    detected_object: Optional[str]
    expected_object: Optional[str]
    message: str
    severity: str    # info, warning, error
    data: Dict = field(default_factory=dict)


# Movement detection thresholds
MOVEMENT_THRESHOLD = 0.015   # normalized: object must move this much to be "moving"
STILL_THRESHOLD = 0.005      # below this = "stationary"
STILL_FRAMES_REQUIRED = 8    # frames object must be still for "place" detection
ZONE_ENTER_FRAMES = 4        # frames in zone before confirming zone entry


class ProcedureFSM:
    """
    Finite State Machine tracking the current procedure step.
    Driven by tracked object states and zone membership changes.
    """

    def __init__(self, procedure: ProcedureConfig):
        self.procedure = procedure
        self.step_records: List[StepRecord] = []
        self.events: List[FSMEvent] = []
        self.current_step_idx: int = 0
        self.session_start_time: float = time.time()
        self._object_zone_history: Dict[str, List[str]] = {}  # obj_id -> recent zones
        self._object_prev_positions: Dict[int, Tuple[float, float]] = {}
        self._object_still_counts: Dict[int, int] = {}
        self._zone_enter_counts: Dict[str, Dict[str, int]] = {}  # obj_id -> {zone_id: count}
        self._step_start_time: Optional[float] = None
        self._current_step_record: Optional[StepRecord] = None
        self._sequence_counter: int = 0
        self._completed_step_ids: List[str] = []
        self._is_complete: bool = False
        self._last_emit_time: float = 0.0

        # Initialize first step
        self._start_step(0)

    # ── Public API ─────────────────────────────────────────────────────────────
    @property
    def current_step(self) -> Optional[ProcedureStep]:
        if self.current_step_idx < len(self.procedure.steps):
            return self.procedure.steps[self.current_step_idx]
        return None

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def completed_steps(self) -> int:
        return len(self._completed_step_ids)

    def update(self, tracked_objects: List[TrackedObject]) -> List[FSMEvent]:
        """
        Call each frame with the current tracked objects.
        Returns any new FSM events generated this frame.
        """
        if self._is_complete or self.current_step is None:
            return []

        new_events = []
        step = self.current_step

        # Map YOLO classes to procedure objects
        proc_objects = self._map_to_proc_objects(tracked_objects)

        # Check for action based on step type
        if step.action in ("pick", "move"):
            event = self._check_pick_move(step, proc_objects, tracked_objects)
            if event:
                new_events.append(event)
        elif step.action == "place":
            event = self._check_place(step, proc_objects, tracked_objects)
            if event:
                new_events.append(event)
        elif step.action == "tool_use":
            event = self._check_tool_use(step, proc_objects, tracked_objects)
            if event:
                new_events.append(event)
        elif step.action == "complete":
            event = self._check_complete(step)
            if event:
                new_events.append(event)

        # Update still counters
        self._update_motion_tracking(tracked_objects)

        # Emit any buffered events
        self.events.extend(new_events)
        return new_events

    def get_snapshot(self) -> Dict[str, Any]:
        """Serializable state snapshot for WebSocket broadcast."""
        step = self.current_step
        return {
            "current_step_idx": self.current_step_idx,
            "current_step": {
                "id": step.id, "name": step.name, "action": step.action,
                "expected_object": step.expected_object,
                "order": step.order,
            } if step else None,
            "completed_steps": self._completed_step_ids,
            "total_steps": len(self.procedure.steps),
            "is_complete": self._is_complete,
            "step_records": [self._record_to_dict(r) for r in self.step_records],
            "elapsed_s": time.time() - self.session_start_time,
        }

    def finish_session(self) -> List[StepRecord]:
        """Called when session ends. Returns all step records."""
        if self._current_step_record and self._current_step_record.state == StepState.IN_PROGRESS:
            self._current_step_record.state = StepState.FAILED
            self._current_step_record.notes = "Session ended before step completion"
        return self.step_records

    # ── Private ────────────────────────────────────────────────────────────────
    def _start_step(self, idx: int):
        if idx >= len(self.procedure.steps):
            self._is_complete = True
            return
        self.current_step_idx = idx
        self._step_start_time = time.time()
        step = self.procedure.steps[idx]
        self._current_step_record = StepRecord(
            step_id=step.id, step_name=step.name,
            expected_object=step.expected_object,
            detected_object=None, state=StepState.IN_PROGRESS,
            started_at=self._step_start_time, completed_at=None,
            duration_s=None, position_at_completion=None,
            trajectory_snapshot=[], sequence_order=idx,
        )
        self.events.append(FSMEvent(
            event_type="step_started", timestamp=time.time(),
            step_id=step.id, step_name=step.name,
            detected_object=None, expected_object=step.expected_object,
            message=f"Step {step.order}: {step.name}", severity="info",
        ))

    def _complete_step(self, step: ProcedureStep, detected_object: Optional[str],
                       position: Optional[List[float]], trajectory: List[Dict],
                       notes: str = "") -> FSMEvent:
        now = time.time()
        duration = now - (self._step_start_time or now)
        if self._current_step_record:
            self._current_step_record.state = StepState.COMPLETED
            self._current_step_record.completed_at = now
            self._current_step_record.duration_s = duration
            self._current_step_record.detected_object = detected_object
            self._current_step_record.position_at_completion = position
            self._current_step_record.trajectory_snapshot = trajectory[-20:]  # last 20 points
            self._current_step_record.notes = notes
            self.step_records.append(self._current_step_record)
        self._completed_step_ids.append(step.id)
        self._sequence_counter += 1

        evt = FSMEvent(
            event_type="step_completed", timestamp=now,
            step_id=step.id, step_name=step.name,
            detected_object=detected_object, expected_object=step.expected_object,
            message=f"✓ {step.name} completed ({duration:.1f}s)",
            severity="info",
            data={"duration_s": duration, "position": position},
        )

        # Advance to next step
        self._start_step(self.current_step_idx + 1)
        return evt

    def _check_pick_move(self, step: ProcedureStep,
                         proc_objects: Dict[str, List[TrackedObject]],
                         all_objects: List[TrackedObject]) -> Optional[FSMEvent]:
        expected_obj_id = step.expected_object
        if not expected_obj_id:
            return self._complete_step(step, None, None, [], "No object required")

        matching = proc_objects.get(expected_obj_id, [])
        if not matching:
            # Check if wrong object is being used
            for pid, objs in proc_objects.items():
                if objs and pid != expected_obj_id and step.source_zone:
                    # Object from wrong source
                    pass
            return None

        obj = matching[0]  # Use first matching tracked object

        # Check movement: object moving away from source zone
        if step.source_zone and step.source_zone in obj.current_zones:
            return None  # Still in source zone, not picked yet

        # Object is NOT in source zone anymore — pick detected
        traj = obj.history[-30:] if len(obj.history) >= 30 else obj.history
        pos = obj.center
        return self._complete_step(
            step, expected_obj_id, pos, traj,
            f"Object detected leaving source zone"
        )

    def _check_place(self, step: ProcedureStep,
                     proc_objects: Dict[str, List[TrackedObject]],
                     all_objects: List[TrackedObject]) -> Optional[FSMEvent]:
        expected_obj_id = step.expected_object
        target_zone = step.target_zone
        if not expected_obj_id or not target_zone:
            return self._complete_step(step, expected_obj_id, None, [])

        matching = proc_objects.get(expected_obj_id, [])
        if not matching:
            return None

        obj = matching[0]

        # Must be in target zone AND stationary
        in_zone = target_zone in obj.current_zones
        still_count = self._object_still_counts.get(obj.track_id, 0)
        is_still = still_count >= STILL_FRAMES_REQUIRED

        if in_zone and is_still:
            traj = obj.history[-30:]
            return self._complete_step(
                step, expected_obj_id, obj.center, traj,
                f"Object placed in {target_zone}, stationary"
            )
        return None

    def _check_tool_use(self, step: ProcedureStep,
                        proc_objects: Dict[str, List[TrackedObject]],
                        all_objects: List[TrackedObject]) -> Optional[FSMEvent]:
        expected_obj_id = step.expected_object  # "tool"
        target_zone = step.target_zone

        matching = proc_objects.get(expected_obj_id or "tool", [])
        if not matching:
            return None

        obj = matching[0]
        in_zone = target_zone in obj.current_zones if target_zone else True
        still_count = self._object_still_counts.get(obj.track_id, 0)

        if in_zone and still_count >= STILL_FRAMES_REQUIRED:
            traj = obj.history[-30:]
            return self._complete_step(step, expected_obj_id, obj.center, traj, "Tool used")
        return None

    def _check_complete(self, step: ProcedureStep) -> Optional[FSMEvent]:
        """Complete step for the final "complete" action."""
        evt = self._complete_step(step, None, None, [], "Procedure complete")
        self._is_complete = True
        return evt

    def _map_to_proc_objects(self, tracked: List[TrackedObject]) -> Dict[str, List[TrackedObject]]:
        """Map tracked objects to procedure object IDs based on YOLO class."""
        result: Dict[str, List[TrackedObject]] = {}
        for obj in tracked:
            proc_obj = get_object_by_yolo_class(self.procedure, obj.class_name)
            if proc_obj:
                result.setdefault(proc_obj.id, []).append(obj)
        return result

    def _update_motion_tracking(self, tracked: List[TrackedObject]):
        for obj in tracked:
            tid = obj.track_id
            prev = self._object_prev_positions.get(tid)
            curr = (obj.center[0], obj.center[1])
            if prev is not None:
                dist = math.hypot(curr[0] - prev[0], curr[1] - prev[1])
                if dist < STILL_THRESHOLD:
                    self._object_still_counts[tid] = self._object_still_counts.get(tid, 0) + 1
                else:
                    self._object_still_counts[tid] = 0
            else:
                self._object_still_counts[tid] = 0
            self._object_prev_positions[tid] = curr

    @staticmethod
    def _record_to_dict(r: StepRecord) -> Dict:
        return {
            "step_id": r.step_id, "step_name": r.step_name,
            "state": r.state.value,
            "expected_object": r.expected_object,
            "detected_object": r.detected_object,
            "started_at": r.started_at, "completed_at": r.completed_at,
            "duration_s": r.duration_s,
            "position_at_completion": r.position_at_completion,
            "sequence_order": r.sequence_order,
            "notes": r.notes,
        }
