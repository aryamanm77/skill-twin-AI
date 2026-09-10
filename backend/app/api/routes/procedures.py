"""Procedure and domain routes."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Any
from app.database.db import get_db
from app.database import crud
from app.database.models import UserRole
from app.api.routes.auth import get_current_user, require_role
from app.procedure_engine.loader import load_procedure, parse_procedure
from app.core.config import CONFIG_DIR

router = APIRouter(prefix="/procedures", tags=["procedures"])


class ProcedureCreateRequest(BaseModel):
    config: dict


@router.get("/domains")
def list_domains(db: Session = Depends(get_db)):
    domains = crud.list_domains(db)
    return [{"id": d.id, "name": d.name, "icon": d.icon, "description": d.description}
            for d in domains]


@router.get("")
def list_procedures(domain_id: Optional[str] = None, db: Session = Depends(get_db)):
    procs = crud.list_procedures(db, domain_id=domain_id)
    return [
        {
            "id": p.id, "name": p.name, "description": p.description,
            "domain_id": p.domain_id, "version": p.version,
            "steps_count": len(p.config_json.get("steps", [])),
        }
        for p in procs
    ]


@router.get("/{procedure_id}")
def get_procedure(procedure_id: str, db: Session = Depends(get_db)):
    proc = crud.get_procedure(db, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    return proc.config_json


@router.post("")
def create_procedure(
    request: ProcedureCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role(UserRole.ADMIN, UserRole.EXPERT))
):
    config = request.config
    if "id" not in config or "name" not in config:
        raise HTTPException(status_code=400, detail="Procedure config must have 'id' and 'name'")
    # Validate by parsing
    try:
        parse_procedure(config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid procedure config: {e}")
    # Save to file
    proc_file = CONFIG_DIR / "procedures" / f"{config['id']}.json"
    proc_file.write_text(json.dumps(config, indent=2))
    # Save to DB
    if crud.get_procedure(db, config["id"]):
        proc = crud.get_procedure(db, config["id"])
        proc.config_json = config
        proc.name = config["name"]
        db.commit()
    else:
        crud.create_procedure(db, config)
    return {"status": "ok", "id": config["id"]}


@router.get("/{procedure_id}/expert-profile")
def get_expert_profile(procedure_id: str, db: Session = Depends(get_db)):
    profile = crud.get_active_expert_profile(db, procedure_id)
    if not profile:
        return {"has_profile": False}
    return {
        "has_profile": True,
        "session_id": profile.session_id,
        "recorded_at": profile.recorded_at.isoformat(),
        "total_duration_s": profile.total_duration_s,
        "step_count": len(profile.step_data),
        "step_data": profile.step_data,
        "trajectory_data": profile.trajectory_data,
    }
