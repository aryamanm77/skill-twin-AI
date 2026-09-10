"""Tests for sequence comparator."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest
from app.procedure_engine.loader import parse_procedure
from app.procedure_engine.fsm import StepRecord, StepState
from app.procedure_engine.comparator import compare, _path_length

PROC = {
    "id": "comparator_test",
    "name": "Comparator Test",
    "domain": "manufacturing",
    "description": "",
    "version": "1.0",
    "scoring_weights": {"sequence": 0.3, "object_accuracy": 0.25, "position": 0.2, "timing": 0.15, "movement": 0.1},
    "tolerances": {"position_px": 80, "timing_factor": 2.5, "trajectory_dtw": 0.4},
    "workspace_zones": [],
    "objects": [
        {"id": "a", "name": "A", "display_name": "A", "yolo_classes": ["bottle"], "color": "#fff", "source_zone": None},
        {"id": "b", "name": "B", "display_name": "B", "yolo_classes": ["remote"], "color": "#000", "source_zone": None},
    ],
    "steps": [
        {"id": "s1", "order": 1, "name": "S1", "description": "", "action": "pick",
         "expected_object": "a", "source_zone": None, "target_zone": None,
         "expected_duration_s": 3.0, "max_duration_s": 10.0, "min_duration_s": 0.5},
        {"id": "s2", "order": 2, "name": "S2", "description": "", "action": "pick",
         "expected_object": "b", "source_zone": None, "target_zone": None,
         "expected_duration_s": 3.0, "max_duration_s": 10.0, "min_duration_s": 0.5},
    ],
}

EXPERT = [
    {"step_id": "s1", "step_name": "S1", "state": "completed", "expected_object": "a",
     "detected_object": "a", "duration_s": 3.0, "position_at_completion": [0.5, 0.5],
     "trajectory_snapshot": [{"cx": 0.1, "cy": 0.8}, {"cx": 0.5, "cy": 0.5}]},
    {"step_id": "s2", "step_name": "S2", "state": "completed", "expected_object": "b",
     "detected_object": "b", "duration_s": 3.5, "position_at_completion": [0.6, 0.4],
     "trajectory_snapshot": [{"cx": 0.2, "cy": 0.8}, {"cx": 0.6, "cy": 0.4}]},
]


def make_rec(sid, name, exp_obj, det_obj, state=StepState.COMPLETED, dur=3.0, pos=None, traj=None):
    return StepRecord(
        step_id=sid, step_name=name, expected_object=exp_obj, detected_object=det_obj,
        state=state, started_at=0.0, completed_at=dur, duration_s=dur,
        position_at_completion=pos or [0.5, 0.5],
        trajectory_snapshot=traj or [{"cx": 0.5, "cy": 0.5}],
        sequence_order=0,
    )


class TestComparator:
    def test_perfect_match(self):
        proc = parse_procedure(PROC)
        trainee = [make_rec("s1", "S1", "a", "a"), make_rec("s2", "S2", "b", "b")]
        result = compare(proc, EXPERT, trainee)
        assert result.object_accuracy == 1.0
        assert len(result.wrong_object_events) == 0

    def test_wrong_object_detected(self):
        proc = parse_procedure(PROC)
        trainee = [
            make_rec("s1", "S1", "a", "b"),  # Used B instead of A
            make_rec("s2", "S2", "b", "b"),
        ]
        result = compare(proc, EXPERT, trainee)
        assert result.object_accuracy < 1.0
        assert len(result.wrong_object_events) == 1
        assert result.wrong_object_events[0]["expected"] == "a"
        assert result.wrong_object_events[0]["detected"] == "b"

    def test_timing_deviation_large(self):
        proc = parse_procedure(PROC)
        trainee = [
            make_rec("s1", "S1", "a", "a", dur=12.0),  # 4x slower
            make_rec("s2", "S2", "b", "b"),
        ]
        result = compare(proc, EXPERT, trainee)
        assert any(c.timing_score < 1.0 for c in result.step_comparisons)

    def test_path_length_calculation(self):
        traj = [{"cx": 0.0, "cy": 0.0}, {"cx": 0.3, "cy": 0.4}]
        length = _path_length(traj)
        assert abs(length - 0.5) < 0.001  # 3-4-5 right triangle scaled

    def test_empty_trajectories(self):
        assert _path_length([]) == 0.0
        assert _path_length([{"cx": 0.5, "cy": 0.5}]) == 0.0

    def test_steps_completed_count(self):
        proc = parse_procedure(PROC)
        trainee = [
            make_rec("s1", "S1", "a", "a"),
            make_rec("s2", "S2", "b", "b", state=StepState.FAILED),
        ]
        result = compare(proc, EXPERT, trainee)
        assert result.steps_completed == 1

    def test_both_sequences_recorded(self):
        proc = parse_procedure(PROC)
        trainee = [make_rec("s1", "S1", "a", "a"), make_rec("s2", "S2", "b", "b")]
        result = compare(proc, EXPERT, trainee)
        assert "s1" in result.detected_sequence
        assert "s2" in result.detected_sequence
