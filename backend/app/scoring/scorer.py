"""
Skill scoring engine.

Produces a transparent, weighted skill score from comparison metrics.
All scores derive from real measurements. No random or hardcoded values.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
from app.procedure_engine.loader import ProcedureConfig, ScoringWeights
from app.procedure_engine.comparator import ComparisonResult, StepComparison


@dataclass
class SkillScore:
    final_score: float      # 0-100
    sequence: float         # 0-100
    object_accuracy: float  # 0-100
    position: float         # 0-100
    timing: float           # 0-100
    movement: float         # 0-100
    weights: Dict[str, float]
    steps_completed: int
    total_steps: int
    explanation: List[str]
    step_scores: List[Dict]


def compute_score(procedure: ProcedureConfig,
                  comparison: ComparisonResult) -> SkillScore:
    """
    Compute weighted skill score from comparison results.
    All values sourced from actual measurements.
    """
    w = procedure.scoring_weights
    weights = {
        "sequence": w.sequence,
        "object_accuracy": w.object_accuracy,
        "position": w.position,
        "timing": w.timing,
        "movement": w.movement,
    }

    # Raw scores (0-1)
    seq = comparison.sequence_accuracy
    obj = comparison.object_accuracy
    pos = comparison.position_accuracy
    tim = comparison.timing_accuracy
    mov = comparison.movement_efficiency

    # Weighted final score (0-100)
    final = (
        seq * w.sequence +
        obj * w.object_accuracy +
        pos * w.position +
        tim * w.timing +
        mov * w.movement
    ) * 100

    # Completion penalty: if not all steps done, cap score
    completion_ratio = comparison.steps_completed / max(comparison.total_steps, 1)
    if completion_ratio < 1.0:
        final = final * completion_ratio

    explanation = _build_explanation(comparison, w)
    step_scores = _build_step_scores(comparison.step_comparisons)

    return SkillScore(
        final_score=round(final, 1),
        sequence=round(seq * 100, 1),
        object_accuracy=round(obj * 100, 1),
        position=round(pos * 100, 1),
        timing=round(tim * 100, 1),
        movement=round(mov * 100, 1),
        weights=weights,
        steps_completed=comparison.steps_completed,
        total_steps=comparison.total_steps,
        explanation=explanation,
        step_scores=step_scores,
    )


def _build_explanation(comparison: ComparisonResult, weights: ScoringWeights) -> List[str]:
    explanations = []

    if comparison.wrong_object_events:
        for e in comparison.wrong_object_events:
            explanations.append(f"⚠ {e['message']}")

    if comparison.sequence_deviations:
        for d in comparison.sequence_deviations:
            explanations.append(f"⚠ {d['message']}")

    for sc in comparison.step_comparisons:
        for dev in sc.deviations:
            explanations.append(f"• {sc.step_name}: {dev}")

    if not explanations:
        if comparison.steps_completed == comparison.total_steps:
            explanations.append("✓ All steps completed correctly.")
        else:
            explanations.append(
                f"ℹ {comparison.steps_completed}/{comparison.total_steps} steps completed."
            )

    return explanations


def _build_step_scores(step_comparisons: List[StepComparison]) -> List[Dict]:
    result = []
    for sc in step_comparisons:
        avg = (sc.sequence_score + sc.object_score + sc.position_score
               + sc.timing_score + sc.movement_score) / 5
        result.append({
            "step_id": sc.step_id,
            "step_name": sc.step_name,
            "completed": sc.completed,
            "score": round(avg * 100, 1),
            "sequence": round(sc.sequence_score * 100, 1),
            "object": round(sc.object_score * 100, 1),
            "position": round(sc.position_score * 100, 1),
            "timing": round(sc.timing_score * 100, 1),
            "movement": round(sc.movement_score * 100, 1),
            "deviations": sc.deviations,
        })
    return result


def score_to_dict(score: SkillScore) -> Dict:
    return {
        "final_score": score.final_score,
        "sequence": score.sequence,
        "object_accuracy": score.object_accuracy,
        "position": score.position,
        "timing": score.timing,
        "movement": score.movement,
        "weights": score.weights,
        "steps_completed": score.steps_completed,
        "total_steps": score.total_steps,
        "explanation": score.explanation,
        "step_scores": score.step_scores,
    }
