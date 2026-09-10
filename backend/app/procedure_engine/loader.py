"""
Procedure loader: reads and validates procedure JSON configs.
"""
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from app.core.config import CONFIG_DIR


@dataclass
class ProcedureStep:
    id: str
    order: int
    name: str
    description: str
    action: str                   # pick, move, place, tool_use, complete
    expected_object: Optional[str]
    source_zone: Optional[str]
    target_zone: Optional[str]
    expected_duration_s: float
    max_duration_s: float
    min_duration_s: float


@dataclass
class ProcedureObject:
    id: str
    name: str
    display_name: str
    yolo_classes: List[str]
    color: str
    source_zone: Optional[str]


@dataclass
class ScoringWeights:
    sequence: float = 0.30
    object_accuracy: float = 0.25
    position: float = 0.20
    timing: float = 0.15
    movement: float = 0.10


@dataclass
class ProcedureTolerance:
    position_px: float = 80.0
    timing_factor: float = 2.5
    trajectory_dtw: float = 0.40


@dataclass
class ProcedureConfig:
    id: str
    name: str
    domain: str
    description: str
    version: str
    steps: List[ProcedureStep]
    objects: List[ProcedureObject]
    workspace_zones: List[Dict]
    scoring_weights: ScoringWeights
    tolerances: ProcedureTolerance
    raw: Dict[str, Any]   # original JSON


def load_procedure(procedure_id: str) -> Optional[ProcedureConfig]:
    """Load procedure from config file."""
    proc_file = CONFIG_DIR / "procedures" / f"{procedure_id}.json"
    if not proc_file.exists():
        return None
    return parse_procedure(json.loads(proc_file.read_text()))


def parse_procedure(data: Dict[str, Any]) -> ProcedureConfig:
    """Parse raw JSON dict into ProcedureConfig."""
    steps = [
        ProcedureStep(
            id=s["id"], order=s["order"], name=s["name"],
            description=s.get("description", ""),
            action=s["action"],
            expected_object=s.get("expected_object"),
            source_zone=s.get("source_zone"),
            target_zone=s.get("target_zone"),
            expected_duration_s=s.get("expected_duration_s", 3.0),
            max_duration_s=s.get("max_duration_s", 15.0),
            min_duration_s=s.get("min_duration_s", 0.5),
        )
        for s in sorted(data.get("steps", []), key=lambda x: x["order"])
    ]
    objects = [
        ProcedureObject(
            id=o["id"], name=o["name"], display_name=o.get("display_name", o["name"]),
            yolo_classes=o.get("yolo_classes", []),
            color=o.get("color", "#888"),
            source_zone=o.get("source_zone"),
        )
        for o in data.get("objects", [])
    ]
    w = data.get("scoring_weights", {})
    tol = data.get("tolerances", {})
    return ProcedureConfig(
        id=data["id"], name=data["name"], domain=data["domain"],
        description=data.get("description", ""), version=data.get("version", "1.0"),
        steps=steps, objects=objects,
        workspace_zones=data.get("workspace_zones", []),
        scoring_weights=ScoringWeights(
            sequence=w.get("sequence", 0.30),
            object_accuracy=w.get("object_accuracy", 0.25),
            position=w.get("position", 0.20),
            timing=w.get("timing", 0.15),
            movement=w.get("movement", 0.10),
        ),
        tolerances=ProcedureTolerance(
            position_px=tol.get("position_px", 80),
            timing_factor=tol.get("timing_factor", 2.5),
            trajectory_dtw=tol.get("trajectory_dtw", 0.40),
        ),
        raw=data,
    )


def get_object_by_yolo_class(proc: ProcedureConfig, class_name: str) -> Optional[ProcedureObject]:
    """Map a YOLO class name to a procedure object."""
    for obj in proc.objects:
        if class_name in obj.yolo_classes:
            return obj
    return None
