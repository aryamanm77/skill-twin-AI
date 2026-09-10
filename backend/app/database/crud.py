"""CRUD operations for all database entities."""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.database.models import (
    User, Domain, Procedure, ExpertProfile, TrainingSession,
    UserRole, SessionStatus, SessionMode
)
from app.core.security import verify_password, hash_password


# ─── Users ────────────────────────────────────────────────────────────────────
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if user and verify_password(password, user.hashed_password):
        return user
    return None

def create_user(db: Session, username: str, email: str, full_name: str,
                password: str, role: UserRole = UserRole.TRAINEE) -> User:
    user = User(
        username=username, email=email, full_name=full_name,
        hashed_password=hash_password(password), role=role,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user

def list_users(db: Session) -> List[User]:
    return list(db.execute(select(User)).scalars())


# ─── Domains ──────────────────────────────────────────────────────────────────
def list_domains(db: Session) -> List[Domain]:
    return list(db.execute(select(Domain).where(Domain.is_active == True)).scalars())

def get_domain(db: Session, domain_id: str) -> Optional[Domain]:
    return db.get(Domain, domain_id)


# ─── Procedures ───────────────────────────────────────────────────────────────
def list_procedures(db: Session, domain_id: Optional[str] = None) -> List[Procedure]:
    q = select(Procedure).where(Procedure.is_active == True)
    if domain_id:
        q = q.where(Procedure.domain_id == domain_id)
    return list(db.execute(q).scalars())

def get_procedure(db: Session, proc_id: str) -> Optional[Procedure]:
    return db.get(Procedure, proc_id)

def create_procedure(db: Session, data: dict) -> Procedure:
    proc = Procedure(
        id=data["id"], name=data["name"], description=data.get("description", ""),
        domain_id=data["domain"], version=data.get("version", "1.0"),
        config_json=data, scoring_weights=data.get("scoring_weights"),
    )
    db.add(proc); db.commit(); db.refresh(proc)
    return proc


# ─── Expert Profiles ──────────────────────────────────────────────────────────
def save_expert_profile(db: Session, session_id: str, procedure_id: str,
                        recorded_by: int, step_data: list,
                        trajectory_data: dict, total_duration: float,
                        notes: str = "") -> ExpertProfile:
    # deactivate previous profiles for this procedure
    prev = db.execute(
        select(ExpertProfile).where(ExpertProfile.procedure_id == procedure_id)
    ).scalars().all()
    for p in prev:
        p.is_active = False

    profile = ExpertProfile(
        session_id=session_id, procedure_id=procedure_id, recorded_by=recorded_by,
        step_data=step_data, trajectory_data=trajectory_data,
        total_duration_s=total_duration, notes=notes, is_active=True,
    )
    db.add(profile); db.commit(); db.refresh(profile)
    return profile

def get_active_expert_profile(db: Session, procedure_id: str) -> Optional[ExpertProfile]:
    return db.execute(
        select(ExpertProfile).where(
            ExpertProfile.procedure_id == procedure_id,
            ExpertProfile.is_active == True,
        )
    ).scalar_one_or_none()

def list_expert_profiles(db: Session, procedure_id: str) -> List[ExpertProfile]:
    return list(db.execute(
        select(ExpertProfile)
        .where(ExpertProfile.procedure_id == procedure_id)
        .order_by(desc(ExpertProfile.recorded_at))
    ).scalars())


# ─── Training Sessions ────────────────────────────────────────────────────────
def create_session(db: Session, session_id: str, user_id: int,
                   procedure_id: str, mode: SessionMode) -> TrainingSession:
    s = TrainingSession(
        id=session_id, user_id=user_id, procedure_id=procedure_id,
        mode=mode, status=SessionStatus.ACTIVE,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s

def get_session(db: Session, session_id: str) -> Optional[TrainingSession]:
    return db.get(TrainingSession, session_id)

def complete_session(db: Session, session_id: str, scores: dict,
                     step_results: list, trajectory_data: dict,
                     events: list, explanation: list) -> Optional[TrainingSession]:
    s = db.get(TrainingSession, session_id)
    if not s:
        return None
    s.status = SessionStatus.COMPLETED
    s.ended_at = datetime.now(timezone.utc)
    s.total_duration_s = scores.get("total_duration", 0)
    s.final_score = scores.get("final_score", 0)
    s.sequence_score = scores.get("sequence", 0)
    s.object_score = scores.get("object_accuracy", 0)
    s.position_score = scores.get("position", 0)
    s.timing_score = scores.get("timing", 0)
    s.movement_score = scores.get("movement", 0)
    s.step_results = step_results
    s.trajectory_data = trajectory_data
    s.events = events
    s.score_explanation = explanation
    db.commit(); db.refresh(s)
    return s

def abort_session(db: Session, session_id: str):
    s = db.get(TrainingSession, session_id)
    if s:
        s.status = SessionStatus.ABORTED
        s.ended_at = datetime.now(timezone.utc)
        db.commit()

def list_sessions(db: Session, user_id: Optional[int] = None,
                  procedure_id: Optional[str] = None,
                  mode: Optional[SessionMode] = None,
                  limit: int = 50) -> List[TrainingSession]:
    q = select(TrainingSession).order_by(desc(TrainingSession.started_at)).limit(limit)
    if user_id:
        q = q.where(TrainingSession.user_id == user_id)
    if procedure_id:
        q = q.where(TrainingSession.procedure_id == procedure_id)
    if mode:
        q = q.where(TrainingSession.mode == mode)
    return list(db.execute(q).scalars())
