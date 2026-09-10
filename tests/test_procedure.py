"""
Tests for procedure loader and FSM.
Run with: cd backend && python -m pytest ../tests/ -v
"""
import pytest
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.procedure_engine.loader import load_procedure, parse_procedure, get_object_by_yolo_class
from app.procedure_engine.fsm import ProcedureFSM, StepState, FSMEvent
from app.tracking.tracker import TrackedObject


# ── Fixtures ──────────────────────────────────────────────────────────────────
MINIMAL_PROC = {
    "id": "test_proc",
    "name": "Test Procedure",
    "domain": "manufacturing",
    "description": "Test",
    "version": "1.0",
    "scoring_weights": {"sequence": 0.3, "object_accuracy": 0.25, "position": 0.2, "timing": 0.15, "movement": 0.1},
    "tolerances": {"position_px": 80, "timing_factor": 2.5, "trajectory_dtw": 0.4},
    "workspace_zones": [
        {"id": "source_a", "name": "Source A", "color": "#3B82F6",
         "normalized": {"x": 0.05, "y": 0.6, "w": 0.18, "h": 0.3}},
        {"id": "assembly", "name": "Assembly", "color": "#10B981",
         "normalized": {"x": 0.3, "y": 0.1, "w": 0.4, "h": 0.4}},
    ],
    "objects": [
        {"id": "part_a", "name": "Part A", "display_name": "Part A",
         "yolo_classes": ["bottle"], "color": "#3B82F6", "source_zone": "source_a"},
    ],
    "steps": [
        {"id": "s1", "order": 1, "name": "Pick Part A", "description": "Pick up Part A",
         "action": "pick", "expected_object": "part_a", "source_zone": "source_a",
         "target_zone": None, "expected_duration_s": 3.0, "max_duration_s": 10.0, "min_duration_s": 0.5},
        {"id": "s2", "order": 2, "name": "Place Part A", "description": "Place Part A",
         "action": "place", "expected_object": "part_a", "source_zone": None,
         "target_zone": "assembly", "expected_duration_s": 4.0, "max_duration_s": 15.0, "min_duration_s": 1.0},
        {"id": "s3", "order": 3, "name": "Complete", "description": "Done",
         "action": "complete", "expected_object": None, "source_zone": None,
         "target_zone": None, "expected_duration_s": 1.0, "max_duration_s": 5.0, "min_duration_s": 0.1},
    ]
}


# ── Procedure loader tests ─────────────────────────────────────────────────────
class TestProcedureLoader:
    def test_parse_procedure_minimal(self):
        proc = parse_procedure(MINIMAL_PROC)
        assert proc.id == "test_proc"
        assert proc.name == "Test Procedure"
        assert len(proc.steps) == 3
        assert len(proc.objects) == 1

    def test_steps_sorted_by_order(self):
        data = dict(MINIMAL_PROC)
        data["steps"] = list(reversed(MINIMAL_PROC["steps"]))
        proc = parse_procedure(data)
        orders = [s.order for s in proc.steps]
        assert orders == sorted(orders)

    def test_scoring_weights(self):
        proc = parse_procedure(MINIMAL_PROC)
        assert abs(proc.scoring_weights.sequence - 0.30) < 0.001
        assert abs(proc.scoring_weights.object_accuracy - 0.25) < 0.001
        total = (proc.scoring_weights.sequence + proc.scoring_weights.object_accuracy +
                 proc.scoring_weights.position + proc.scoring_weights.timing +
                 proc.scoring_weights.movement)
        assert abs(total - 1.0) < 0.001

    def test_get_object_by_yolo_class(self):
        proc = parse_procedure(MINIMAL_PROC)
        obj = get_object_by_yolo_class(proc, "bottle")
        assert obj is not None
        assert obj.id == "part_a"

    def test_missing_yolo_class(self):
        proc = parse_procedure(MINIMAL_PROC)
        obj = get_object_by_yolo_class(proc, "nonexistent_class")
        assert obj is None

    def test_load_procedure_from_file(self):
        """Loads the actual basic_assembly.json config file."""
        proc = load_procedure("basic_assembly")
        if proc is None:
            pytest.skip("basic_assembly.json not found — run from correct directory")
        assert proc.id == "basic_assembly"
        assert len(proc.steps) == 7


# ── FSM tests ──────────────────────────────────────────────────────────────────
def make_tracked_obj(track_id: int, class_name: str, cx: float, cy: float,
                     zones: list = None) -> TrackedObject:
    return TrackedObject(
        track_id=track_id, class_name=class_name, confidence=0.9,
        center=[cx, cy], center_px=[int(cx*1280), int(cy*720)],
        bbox=[cx-0.02, cy-0.02, cx+0.02, cy+0.02],
        workspace_pos=[cx, cy], history=[{"ts": time.time(), "cx": cx, "cy": cy,
                                          "cx_px": int(cx*1280), "cy_px": int(cy*720),
                                          "ws_x": cx, "ws_y": cy, "zones": zones or []}],
        last_seen=time.time(), first_seen=time.time(),
        is_active=True, current_zones=zones or [], frames_seen=1,
    )


class TestFSM:
    def test_fsm_initial_state(self):
        proc = parse_procedure(MINIMAL_PROC)
        fsm = ProcedureFSM(proc)
        assert fsm.current_step_idx == 0
        assert fsm.current_step.id == "s1"
        assert not fsm.is_complete

    def test_fsm_step1_pick_triggers_when_object_leaves_source(self):
        proc = parse_procedure(MINIMAL_PROC)
        fsm = ProcedureFSM(proc)

        # Object IS in source zone — should not complete
        obj_in_source = make_tracked_obj(1, "bottle", 0.12, 0.75, zones=["source_a"])
        events = fsm.update([obj_in_source])
        # step_started event was emitted in __init__, update should not complete yet
        step_completed_events = [e for e in events if e.event_type == "step_completed"]
        assert len(step_completed_events) == 0

        # Object leaves source zone — pick detected
        obj_not_in_source = make_tracked_obj(1, "bottle", 0.50, 0.30, zones=[])
        events = fsm.update([obj_not_in_source])
        step_events = [e for e in events if e.event_type == "step_completed"]
        assert len(step_events) == 1
        assert step_events[0].step_id == "s1"

    def test_fsm_advances_to_next_step(self):
        proc = parse_procedure(MINIMAL_PROC)
        fsm = ProcedureFSM(proc)
        # Complete step 1
        obj = make_tracked_obj(1, "bottle", 0.50, 0.30, zones=[])
        fsm.update([obj])
        # Now on step 2
        assert fsm.current_step_idx == 1
        assert fsm.current_step.id == "s2"

    def test_fsm_place_requires_target_zone_and_stationary(self):
        proc = parse_procedure(MINIMAL_PROC)
        fsm = ProcedureFSM(proc)
        # Complete step 1 first
        obj = make_tracked_obj(1, "bottle", 0.50, 0.30, zones=[])
        fsm.update([obj])

        # Object in assembly zone but moving — should not complete yet
        for _ in range(5):
            obj = make_tracked_obj(1, "bottle", 0.50, 0.30, zones=["assembly"])
            fsm.update([obj])
        # Still counts; need 8 still frames
        step_completed = [e for e in fsm.events if e.event_type == "step_completed" and e.step_id == "s2"]
        assert len(step_completed) == 0

        # Enough still frames
        for _ in range(10):
            obj_still = make_tracked_obj(1, "bottle", 0.50, 0.30, zones=["assembly"])
            fsm.update([obj_still])
        step_completed = [e for e in fsm.events if e.event_type == "step_completed" and e.step_id == "s2"]
        assert len(step_completed) == 1

    def test_fsm_complete_step_final(self):
        proc = parse_procedure(MINIMAL_PROC)
        fsm = ProcedureFSM(proc)
        # Complete s1
        fsm.update([make_tracked_obj(1, "bottle", 0.50, 0.30, zones=[])])
        # Complete s2 — 10 still frames in assembly
        for _ in range(10):
            fsm.update([make_tracked_obj(1, "bottle", 0.50, 0.25, zones=["assembly"])])
        # s3 is "complete" action — should auto-complete
        fsm.update([])
        assert fsm.is_complete

    def test_fsm_finish_session_returns_records(self):
        proc = parse_procedure(MINIMAL_PROC)
        fsm = ProcedureFSM(proc)
        records = fsm.finish_session()
        assert isinstance(records, list)
