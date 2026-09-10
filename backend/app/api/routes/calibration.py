"""Calibration routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Tuple
from app.api.routes.auth import get_current_user, require_role
from app.database.models import UserRole
from app.calibration.homography import save_calibration, load_calibration, compute_homography

router = APIRouter(prefix="/calibration", tags=["calibration"])


class CalibrationRequest(BaseModel):
    procedure_id: str
    points: List[List[float]]   # [[x,y], [x,y], [x,y], [x,y]] in pixels
    frame_width: int
    frame_height: int


@router.post("")
def save_cal(
    request: CalibrationRequest,
    user=Depends(require_role(UserRole.ADMIN, UserRole.EXPERT)),
):
    if len(request.points) < 4:
        raise HTTPException(400, "Need exactly 4 calibration points")
    H = compute_homography([(p[0], p[1]) for p in request.points])
    if H is None:
        raise HTTPException(400, "Could not compute homography from provided points")
    save_calibration(
        [(p[0], p[1]) for p in request.points],
        request.procedure_id,
        request.frame_width,
        request.frame_height,
    )
    return {"status": "ok", "procedure_id": request.procedure_id}


@router.get("/{procedure_id}")
def get_cal(procedure_id: str, user=Depends(get_current_user)):
    cal = load_calibration(procedure_id)
    if not cal:
        return {"has_calibration": False}
    return {"has_calibration": True, **cal}
