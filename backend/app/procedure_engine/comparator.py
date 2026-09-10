"""
Trainee vs Expert comparison engine.

Computes measurable deviations from actual recorded data.
Never generates random or hardcoded results.
"""
import math
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from app.procedure_engine.loader import ProcedureConfig
from app.procedure_engine.fsm import StepRecord, StepState


@dataclass
class StepComparison:
    step_id: str
    step_name: str
    # Sequence
    sequence_match: bool
    sequence_score: float           # 0-1
    # Object
    object_match: bool
    expected_object: Optional[str]
    detected_object: Optional[str]
    object_score: float             # 0-1
    # Position
    position_deviation: Optional[float]  # normalized distance
    position_score: float           # 0-1
    # Timing
    expert_duration_s: Optional[float]
    trainee_duration_s: Optional[float]
    timing_deviation_s: Optional[float]
    timing_score: float             # 0-1
    # Movement
    expert_path_length: Optional[float]
    trainee_path_length: Optional[float]
    movement_efficiency: Optional[float]  # 0-1
    movement_score: float           # 0-1
    # Feedback
    deviations: List[str]           # human-readable deviation messages
    completed: bool


@dataclass
class ComparisonResult:
    procedure_id: str
    step_comparisons: List[StepComparison]
    sequence_accuracy: float     # 0-1
    object_accuracy: float       # 0-1
    position_accuracy: float     # 0-1
    timing_accuracy: float       # 0-1
    movement_efficiency: float   # 0-1
    steps_completed: int
    total_steps: int
    detected_sequence: List[str]
    expected_sequence: List[str]
    wrong_object_events: List[Dict]
    sequence_deviations: List[Dict]


def compare(procedure: ProcedureConfig,
            expert_steps: List[Dict],
            trainee_steps: List[StepRecord]) -> ComparisonResult:
    """
    Compare trainee step records against expert step data.
    All metrics derived from actual measurements.
    """
    expected_seq = [s["step_id"] for s in expert_steps if s.get("state") == "completed"]
    detected_seq = [r.step_id for r in trainee_steps if r.state == StepState.COMPLETED]

    step_comparisons = []
    wrong_objects = []
    seq_deviations = []

    # Build expert lookup by step_id
    expert_by_id = {s["step_id"]: s for s in expert_steps}

    for i, trainee_rec in enumerate(trainee_steps):
        expert_rec = expert_by_id.get(trainee_rec.step_id)
        comp = _compare_step(
            procedure, trainee_rec, expert_rec,
            expected_pos=i, actual_pos=i,
            expected_seq=expected_seq, detected_seq=detected_seq,
            tolerance=procedure.tolerances,
        )
        step_comparisons.append(comp)

        if not comp.object_match and trainee_rec.state == StepState.COMPLETED:
            wrong_objects.append({
                "step_id": trainee_rec.step_id,
                "expected": comp.expected_object,
                "detected": comp.detected_object,
                "message": f"Expected {comp.expected_object}, detected {comp.detected_object}",
            })

        if not comp.sequence_match and trainee_rec.state == StepState.COMPLETED:
            seq_deviations.append({
                "step_id": trainee_rec.step_id,
                "step_name": trainee_rec.step_name,
                "message": f"Sequence deviation at step {trainee_rec.step_name}",
            })

    # Aggregate
    completed_comps = [c for c in step_comparisons if c.completed]
    n = len(completed_comps) or 1

    return ComparisonResult(
        procedure_id=procedure.id,
        step_comparisons=step_comparisons,
        sequence_accuracy=sum(c.sequence_score for c in completed_comps) / n,
        object_accuracy=sum(c.object_score for c in completed_comps) / n,
        position_accuracy=sum(c.position_score for c in completed_comps) / n,
        timing_accuracy=sum(c.timing_score for c in completed_comps) / n,
        movement_efficiency=sum(c.movement_score for c in completed_comps) / n,
        steps_completed=len([r for r in trainee_steps if r.state == StepState.COMPLETED]),
        total_steps=len(procedure.steps),
        detected_sequence=detected_seq,
        expected_sequence=expected_seq,
        wrong_object_events=wrong_objects,
        sequence_deviations=seq_deviations,
    )


def _compare_step(procedure: ProcedureConfig, trainee: StepRecord,
                  expert: Optional[Dict],
                  expected_pos: int, actual_pos: int,
                  expected_seq: List[str], detected_seq: List[str],
                  tolerance) -> StepComparison:
    deviations = []
    completed = trainee.state == StepState.COMPLETED

    # ── Sequence ──────────────────────────────────────────────────────────────
    seq_match = True
    if expected_pos < len(expected_seq) and expected_pos < len(detected_seq):
        seq_match = expected_seq[expected_pos] == detected_seq[actual_pos] if actual_pos < len(detected_seq) else False
    seq_score = 1.0 if seq_match else 0.4

    # ── Object accuracy ───────────────────────────────────────────────────────
    expected_obj = trainee.expected_object
    detected_obj = trainee.detected_object
    obj_match = (expected_obj == detected_obj) or (expected_obj is None)
    obj_score = 1.0 if obj_match else 0.0
    if not obj_match:
        deviations.append(f"Wrong component: expected {expected_obj}, detected {detected_obj}")

    # ── Position ──────────────────────────────────────────────────────────────
    pos_dev = None
    pos_score = 1.0
    if (expert and expert.get("position_at_completion")
            and trainee.position_at_completion):
        ep = expert["position_at_completion"]
        tp = trainee.position_at_completion
        pos_dev = math.hypot(ep[0] - tp[0], ep[1] - tp[1])
        # Normalize: tolerance_px is in normalized units (already normalized)
        tol_norm = tolerance.position_px / 1280  # convert px tolerance to normalized
        if pos_dev <= tol_norm:
            pos_score = 1.0
        elif pos_dev <= tol_norm * 2:
            pos_score = 0.7
        elif pos_dev <= tol_norm * 4:
            pos_score = 0.4
        else:
            pos_score = 0.1
            deviations.append(f"Position deviation: {pos_dev:.3f} (normalized)")

    # ── Timing ────────────────────────────────────────────────────────────────
    expert_dur = expert.get("duration_s") if expert else None
    trainee_dur = trainee.duration_s
    timing_dev = None
    timing_score = 1.0
    if expert_dur and trainee_dur:
        timing_dev = abs(trainee_dur - expert_dur)
        ratio = trainee_dur / max(expert_dur, 0.1)
        if ratio <= tolerance.timing_factor:
            timing_score = max(0.3, 1.0 - (ratio - 1.0) * 0.3)
        else:
            timing_score = 0.2
            deviations.append(
                f"Timing deviation: {timing_dev:.1f}s "
                f"(expert: {expert_dur:.1f}s, trainee: {trainee_dur:.1f}s)"
            )

    # ── Movement ──────────────────────────────────────────────────────────────
    expert_path = None
    trainee_path = None
    movement_efficiency = None
    mov_score = 1.0
    if expert and expert.get("trajectory_snapshot") and trainee.trajectory_snapshot:
        expert_path = _path_length(expert["trajectory_snapshot"])
        trainee_path = _path_length(trainee.trajectory_snapshot)
        if expert_path > 0.001:
            ratio = trainee_path / expert_path
            movement_efficiency = min(1.0, expert_path / max(trainee_path, 0.001))
            if ratio <= 1.0 + tolerance.trajectory_dtw:
                mov_score = movement_efficiency
            else:
                mov_score = max(0.2, movement_efficiency)
                deviations.append(
                    f"Movement path {(ratio-1)*100:.0f}% longer than expert"
                )

    return StepComparison(
        step_id=trainee.step_id, step_name=trainee.step_name,
        sequence_match=seq_match, sequence_score=seq_score,
        object_match=obj_match, expected_object=expected_obj, detected_object=detected_obj,
        object_score=obj_score,
        position_deviation=pos_dev, position_score=pos_score,
        expert_duration_s=expert_dur, trainee_duration_s=trainee_dur,
        timing_deviation_s=timing_dev, timing_score=timing_score,
        expert_path_length=expert_path, trainee_path_length=trainee_path,
        movement_efficiency=movement_efficiency, movement_score=mov_score,
        deviations=deviations, completed=completed,
    )


def _path_length(trajectory: List[Dict]) -> float:
    """Compute total path length from trajectory snapshot."""
    total = 0.0
    for i in range(1, len(trajectory)):
        try:
            dx = trajectory[i]["cx"] - trajectory[i-1]["cx"]
            dy = trajectory[i]["cy"] - trajectory[i-1]["cy"]
            total += math.hypot(dx, dy)
        except (KeyError, TypeError):
            pass
    return total
