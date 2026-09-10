"""Session management routes: start/stop expert & trainee sessions."""
import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional, List
from app.database.db import get_db
from app.database import crud
from app.database.models import UserRole, SessionMode
from app.api.routes.auth import get_current_user
from app.vision.camera import restart_camera, CameraMode
from app.vision.pipeline import get_pipeline
from app.api.ws_manager import manager, WSMessage

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    procedure_id: str
    mode: str          # "expert" or "trainee"
    camera_mode: str = "test"   # "real", "test", "video"
    camera_source: Optional[str] = None   # webcam index or video file path


class SessionResponse(BaseModel):
    session_id: str
    procedure_id: str
    mode: str
    status: str
    started_at: str


@router.post("/start", response_model=SessionResponse)
async def start_session(
    request: StartSessionRequest,
    req: Request,
    db: DBSession = Depends(get_db),
    user=Depends(get_current_user),
):
    pipeline = get_pipeline()
    if pipeline.is_running:
        pipeline.stop_session()

    proc = crud.get_procedure(db, request.procedure_id)
    if not proc:
        raise HTTPException(404, "Procedure not found")

    # For trainee mode, check expert profile exists
    expert_steps = None
    if request.mode == "trainee":
        profile = crud.get_active_expert_profile(db, request.procedure_id)
        if not profile:
            raise HTTPException(400, "No expert profile recorded for this procedure. Record expert first.")
        expert_steps = profile.step_data

    session_id = str(uuid.uuid4())[:8].upper()
    mode = SessionMode.EXPERT if request.mode == "expert" else SessionMode.TRAINEE

    # DB record
    crud.create_session(db, session_id, user.id, request.procedure_id, mode)

    # Camera
    cam_mode = CameraMode(request.camera_mode) if request.camera_mode in ("real", "video", "test") else CameraMode.TEST
    camera = restart_camera(cam_mode, request.camera_source)

    # Get event loop for pipeline → WS async bridge
    loop = asyncio.get_event_loop()

    pipeline.start_session(
        session_id=session_id,
        procedure_config=proc.config_json,
        mode=request.mode,
        camera=camera,
        expert_steps=expert_steps,
        event_loop=loop,
    )

    await manager.broadcast(WSMessage.session_status("started", session_id, request.mode))

    return SessionResponse(
        session_id=session_id,
        procedure_id=request.procedure_id,
        mode=request.mode,
        status="active",
        started_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/{session_id}/stop")
async def stop_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    user=Depends(get_current_user),
):
    pipeline = get_pipeline()
    if not pipeline.is_running or pipeline.session_id != session_id:
        raise HTTPException(400, "Session not active")

    result = pipeline.stop_session()

    if result and result.get("score"):
        score = result["score"]
        crud.complete_session(
            db, session_id,
            scores={
                "final_score": score["final_score"],
                "sequence": score["sequence"],
                "object_accuracy": score["object_accuracy"],
                "position": score["position"],
                "timing": score["timing"],
                "movement": score["movement"],
                "total_duration": score.get("total_duration", 0),
            },
            step_results=result.get("step_records", []),
            trajectory_data=result.get("trajectory_data", {}),
            events=result.get("events", []),
            explanation=score.get("explanation", []),
        )
    elif pipeline.mode == "expert" and result:
        # Save expert profile
        proc = crud.get_procedure(db, pipeline._procedure.id if pipeline._procedure else "")
        if proc:
            crud.save_expert_profile(
                db, session_id=session_id,
                procedure_id=proc.id,
                recorded_by=user.id,
                step_data=result.get("step_records", []),
                trajectory_data=result.get("trajectory_data", {}),
                total_duration=result.get("total_duration_s", 0),
            )
        crud.abort_session(db, session_id)  # Expert sessions aren't "scored"
    else:
        crud.abort_session(db, session_id)

    await manager.broadcast(WSMessage.session_status("stopped", session_id, ""))

    return {"status": "stopped", "session_id": session_id, "result": result}


@router.get("/active")
def get_active_session():
    pipeline = get_pipeline()
    return pipeline.get_status()


@router.get("")
def list_sessions(
    procedure_id: Optional[str] = None,
    mode: Optional[str] = None,
    limit: int = 50,
    db: DBSession = Depends(get_db),
    user=Depends(get_current_user),
):
    # Admins see all, others see own
    uid = user.id if user.role == UserRole.TRAINEE else None
    sm = SessionMode(mode) if mode in ("expert", "trainee") else None
    sessions = crud.list_sessions(db, user_id=uid, procedure_id=procedure_id, mode=sm, limit=limit)
    return [
        {
            "id": s.id, "user_id": s.user_id, "procedure_id": s.procedure_id,
            "mode": s.mode.value, "status": s.status.value,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "final_score": s.final_score,
            "total_duration_s": s.total_duration_s,
        }
        for s in sessions
    ]


@router.get("/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db),
                user=Depends(get_current_user)):
    s = crud.get_session(db, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return {
        "id": s.id, "user_id": s.user_id, "procedure_id": s.procedure_id,
        "mode": s.mode.value, "status": s.status.value,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "final_score": s.final_score,
        "sequence_score": s.sequence_score,
        "object_score": s.object_score,
        "position_score": s.position_score,
        "timing_score": s.timing_score,
        "movement_score": s.movement_score,
        "total_duration_s": s.total_duration_s,
        "step_results": s.step_results,
        "trajectory_data": s.trajectory_data,
        "events": s.events,
        "score_explanation": s.score_explanation,
    }
