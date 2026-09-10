"""SQLAlchemy database models."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EXPERT = "expert"
    TRAINEE = "trainee"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"


class SessionMode(str, enum.Enum):
    EXPERT = "expert"
    TRAINEE = "trainee"


# ─── User ────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False)
    full_name = Column(String(128), nullable=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.TRAINEE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sessions = relationship("TrainingSession", back_populates="user")


# ─── Domain ──────────────────────────────────────────────────────────────────
class Domain(Base):
    __tablename__ = "domains"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    icon = Column(String(8), default="🏭")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    procedures = relationship("Procedure", back_populates="domain")


# ─── Procedure ───────────────────────────────────────────────────────────────
class Procedure(Base):
    __tablename__ = "procedures"

    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    domain_id = Column(String(64), ForeignKey("domains.id"), nullable=False)
    version = Column(String(16), default="1.0")
    config_json = Column(JSON, nullable=False)   # full procedure.json stored here
    scoring_weights = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    domain = relationship("Domain", back_populates="procedures")
    sessions = relationship("TrainingSession", back_populates="procedure")
    expert_profiles = relationship("ExpertProfile", back_populates="procedure")


# ─── Expert Profile ───────────────────────────────────────────────────────────
class ExpertProfile(Base):
    __tablename__ = "expert_profiles"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, nullable=False)
    procedure_id = Column(String(64), ForeignKey("procedures.id"), nullable=False)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)   # current reference for procedure
    step_data = Column(JSON, nullable=False)    # list of StepRecord
    trajectory_data = Column(JSON, nullable=True)
    total_duration_s = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    procedure = relationship("Procedure", back_populates="expert_profiles")


# ─── Training Session ─────────────────────────────────────────────────────────
class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    procedure_id = Column(String(64), ForeignKey("procedures.id"), nullable=False)
    mode = Column(SAEnum(SessionMode), nullable=False)
    status = Column(SAEnum(SessionStatus), default=SessionStatus.ACTIVE)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    total_duration_s = Column(Float, nullable=True)

    # Scores
    final_score = Column(Float, nullable=True)
    sequence_score = Column(Float, nullable=True)
    object_score = Column(Float, nullable=True)
    position_score = Column(Float, nullable=True)
    timing_score = Column(Float, nullable=True)
    movement_score = Column(Float, nullable=True)

    # Detailed data (stored as JSON)
    step_results = Column(JSON, nullable=True)
    trajectory_data = Column(JSON, nullable=True)
    events = Column(JSON, nullable=True)
    score_explanation = Column(JSON, nullable=True)

    user = relationship("User", back_populates="sessions")
    procedure = relationship("Procedure", back_populates="sessions")
