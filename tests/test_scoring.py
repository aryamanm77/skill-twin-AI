"""Tests for scoring engine."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest
from app.procedure_engine.loader import parse_procedure
from app.procedure_engine.fsm import StepRecord, StepState
from app.procedure_engine.comparator import compare
from app.scoring.scorer import compute_score, score_to_dict

MINIMAL_PROC = {
    "id": "test_scoring",
    "name": "Scoring Test",
    "domain": "manufacturing",
    "description": "For scoring tests",
    "version": "1.0",
    "scoring_weights": {"sequence": 0.3, "object_accuracy": 0.25, "position": 0.2, "timing": 0.15, "movement": 0.1},
    "tolerances": {"position_px": 80, "timing_factor": 2.5, "trajectory_dtw": 0.4},
    "workspace_zones": [],
    "objects": [
        {"id": "obj_a", "name": "Part A", "display_name": "Part A",
         "yolo_classes": ["bottle"], "color": "#3B82F6", "source_zone": None},
        {"id": "obj_b", "name": "Part B", "display_name": "Part B",
         "yolo_classes": ["remote"], "color": "#8B5CF6", "source_zone": None},
    ],
    "steps": [
        {"id": "s1", "order": 1, "name": "Pick A", "description": "",
         "action": "pick", "expected_object": "obj_a", "source_zone": None,
         "target_zone": None, "expected_duration_s": 3.0, "max_duration_s": 10.0, "min_duration_s": 0.5},
        {"id": "s2", "order": 2, "name": "Pick B", "description": "",
         "action": "pick", "expected_object": "obj_b", "source_zone": None,
         "target_zone": None, "expected_duration_s": 3.0, "max_duration_s": 10.0, "min_duration_s": 0.5},
    ]
}

EXPERT_STEPS = [
    {
        "step_id": "s1", "step_name": "Pick A", "state": "completed",
        "expected_object": "obj_a", "detected_object": "obj_a",
        "started_at": 0.0, "completed_at": 3.0, "duration_s": 3.0,
        "position_at_completion": [0.5, 0.5], "trajectory_snapshot": [
            {"cx": 0.1, "cy": 0.7}, {"cx": 0.3, "cy": 0.5}, {"cx": 0.5, "cy": 0.5}
        ], "sequence_order": 0,
    },
    {
        "step_id": "s2", "step_name": "Pick B", "state": "completed",
        "expected_object": "obj_b", "detected_object": "obj_b",
        "started_at": 3.0, "completed_at": 6.5, "duration_s": 3.5,
        "position_at_completion": [0.6, 0.4], "trajectory_snapshot": [
            {"cx": 0.25, "cy": 0.7}, {"cx": 0.4, "cy": 0.5}, {"cx": 0.6, "cy": 0.4}
        ], "sequence_order": 1,
    }
]


def make_step_record(step_id, step_name, expected_obj, detected_obj,
                     duration=3.0, position=None, traj=None, state=StepState.COMPLETED):
    return StepRecord(
        step_id=step_id, step_name=step_name,
        expected_object=expected_obj, detected_object=detected_obj,
        state=state,
        started_at=0.0, completed_at=duration,
        duration_s=duration, position_at_completion=position or [0.5, 0.5],
        trajectory_snapshot=traj or [{"cx": 0.5, "cy": 0.5}],
        sequence_order=0,
    )


class TestScorer:
    def test_perfect_score(self):
        """Perfect match should yield score near 100."""
        proc = parse_procedure(MINIMAL_PROC)
        trainee = [
            make_step_record("s1", "Pick A", "obj_a", "obj_a", duration=3.0, position=[0.5, 0.5]),
            make_step_record("s2", "Pick B", "obj_b", "obj_b", duration=3.5, position=[0.6, 0.4]),
        ]
        comparison = compare(proc, EXPERT_STEPS, trainee)
        score = compute_score(proc, comparison)
        assert score.final_score >= 80.0, f"Expected score >= 80, got {score.final_score}"
        assert score.object_accuracy == 100.0
        assert score.sequence == 100.0

    def test_wrong_object_reduces_score(self):
        """Using wrong object should reduce object_accuracy."""
        proc = parse_procedure(MINIMAL_PROC)
        trainee = [
            make_step_record("s1", "Pick A", "obj_a", "obj_b"),  # WRONG object
            make_step_record("s2", "Pick B", "obj_b", "obj_b"),
        ]
        comparison = compare(proc, EXPERT_STEPS, trainee)
        score = compute_score(proc, comparison)
        assert score.object_accuracy < 100.0

    def test_timing_deviation(self):
        """Large timing deviation should reduce timing score."""
        proc = parse_procedure(MINIMAL_PROC)
        trainee = [
            make_step_record("s1", "Pick A", "obj_a", "obj_a", duration=12.0),  # 4x slower
            make_step_record("s2", "Pick B", "obj_b", "obj_b", duration=3.5),
        ]
        comparison = compare(proc, EXPERT_STEPS, trainee)
        score = compute_score(proc, comparison)
        assert score.timing < 100.0

    def test_incomplete_session_caps_score(self):
        """Incomplete session (only 1 of 2 steps) should cap score."""
        proc = parse_procedure(MINIMAL_PROC)
        trainee = [
            make_step_record("s1", "Pick A", "obj_a", "obj_a"),
            make_step_record("s2", "Pick B", "obj_b", "obj_b", state=StepState.FAILED),
        ]
        comparison = compare(proc, EXPERT_STEPS, trainee)
        score = compute_score(proc, comparison)
        # 1/2 completion ratio should reduce score
        assert score.final_score < 95.0

    def test_score_not_random(self):
        """Calling compute_score twice should give identical result."""
        proc = parse_procedure(MINIMAL_PROC)
        trainee = [
            make_step_record("s1", "Pick A", "obj_a", "obj_a"),
            make_step_record("s2", "Pick B", "obj_b", "obj_b"),
        ]
        comparison = compare(proc, EXPERT_STEPS, trainee)
        score1 = compute_score(proc, comparison)
        score2 = compute_score(proc, comparison)
        assert score1.final_score == score2.final_score

    def test_score_to_dict_structure(self):
        """score_to_dict should have all required keys."""
        proc = parse_procedure(MINIMAL_PROC)
        trainee = [make_step_record("s1", "Pick A", "obj_a", "obj_a")]
        comparison = compare(proc, EXPERT_STEPS[:1], trainee)
        score = compute_score(proc, comparison)
        d = score_to_dict(score)
        for key in ("final_score", "sequence", "object_accuracy", "position",
                    "timing", "movement", "weights", "explanation", "step_scores"):
            assert key in d, f"Missing key: {key}"

    def test_explanation_not_empty(self):
        """Explanation should always be non-empty."""
        proc = parse_procedure(MINIMAL_PROC)
        trainee = [make_step_record("s1", "Pick A", "obj_a", "obj_b")]  # wrong
        comparison = compare(proc, EXPERT_STEPS[:1], trainee)
        score = compute_score(proc, comparison)
        assert len(score.explanation) > 0
