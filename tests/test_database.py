"""Tests for database CRUD operations."""
import sys
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Base, User, Domain, Procedure, UserRole
from app.database.crud import (
    create_user, get_user_by_username, authenticate_user,
    create_procedure, get_procedure, list_procedures,
    create_session, complete_session, list_sessions,
    save_expert_profile, get_active_expert_profile,
)
from app.database.models import SessionMode, SessionStatus
import uuid


@pytest.fixture
def db():
    """In-memory SQLite test database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    # Seed minimal domain
    session.add(Domain(id="manufacturing", name="Manufacturing", icon="🏭"))
    session.commit()
    yield session
    session.close()


@pytest.fixture
def test_user(db):
    return create_user(db, "testuser", "test@test.com", "Test User", "pass123", UserRole.TRAINEE)


@pytest.fixture
def test_procedure(db):
    config = {
        "id": "test_proc_db",
        "name": "Test Procedure",
        "domain": "manufacturing",
        "description": "DB test procedure",
        "version": "1.0",
        "scoring_weights": {"sequence": 0.3, "object_accuracy": 0.25, "position": 0.2, "timing": 0.15, "movement": 0.1},
        "tolerances": {"position_px": 80, "timing_factor": 2.5, "trajectory_dtw": 0.4},
        "workspace_zones": [],
        "objects": [],
        "steps": [],
    }
    return create_procedure(db, config)


class TestUserCRUD:
    def test_create_user(self, db):
        user = create_user(db, "alice", "alice@test.com", "Alice", "secret")
        assert user.id is not None
        assert user.username == "alice"
        assert user.role == UserRole.TRAINEE

    def test_get_by_username(self, db):
        create_user(db, "bob", "bob@test.com", "Bob", "secret")
        user = get_user_by_username(db, "bob")
        assert user is not None
        assert user.username == "bob"

    def test_missing_user(self, db):
        assert get_user_by_username(db, "nonexistent") is None

    def test_authenticate_success(self, db, test_user):
        result = authenticate_user(db, "testuser", "pass123")
        assert result is not None
        assert result.id == test_user.id

    def test_authenticate_wrong_password(self, db, test_user):
        result = authenticate_user(db, "testuser", "wrongpass")
        assert result is None


class TestProcedureCRUD:
    def test_create_procedure(self, db, test_procedure):
        assert test_procedure.id == "test_proc_db"
        assert test_procedure.name == "Test Procedure"

    def test_get_procedure(self, db, test_procedure):
        p = get_procedure(db, "test_proc_db")
        assert p is not None
        assert p.id == "test_proc_db"

    def test_get_missing_procedure(self, db):
        assert get_procedure(db, "nonexistent") is None

    def test_list_procedures(self, db, test_procedure):
        procs = list_procedures(db)
        assert any(p.id == "test_proc_db" for p in procs)

    def test_list_procedures_by_domain(self, db, test_procedure):
        procs = list_procedures(db, domain_id="manufacturing")
        assert any(p.id == "test_proc_db" for p in procs)
        procs_other = list_procedures(db, domain_id="agriculture")
        assert not any(p.id == "test_proc_db" for p in procs_other)


class TestSessionCRUD:
    def test_create_session(self, db, test_user, test_procedure):
        sid = str(uuid.uuid4())[:8]
        s = create_session(db, sid, test_user.id, test_procedure.id, SessionMode.TRAINEE)
        assert s.id == sid
        assert s.status == SessionStatus.ACTIVE

    def test_complete_session(self, db, test_user, test_procedure):
        sid = str(uuid.uuid4())[:8]
        create_session(db, sid, test_user.id, test_procedure.id, SessionMode.TRAINEE)
        s = complete_session(
            db, sid,
            scores={"final_score": 85.0, "sequence": 90.0, "object_accuracy": 88.0,
                    "position": 80.0, "timing": 75.0, "movement": 82.0, "total_duration": 45.0},
            step_results=[],
            trajectory_data={},
            events=[],
            explanation=["All steps completed"],
        )
        assert s is not None
        assert s.status == SessionStatus.COMPLETED
        assert abs(s.final_score - 85.0) < 0.01

    def test_list_sessions(self, db, test_user, test_procedure):
        sid = str(uuid.uuid4())[:8]
        create_session(db, sid, test_user.id, test_procedure.id, SessionMode.TRAINEE)
        sessions = list_sessions(db)
        assert any(s.id == sid for s in sessions)


class TestExpertProfile:
    def test_save_expert_profile(self, db, test_user, test_procedure):
        profile = save_expert_profile(
            db, session_id="EXPERT01", procedure_id=test_procedure.id,
            recorded_by=test_user.id,
            step_data=[{"step_id": "s1", "duration_s": 3.0}],
            trajectory_data={},
            total_duration=25.0,
        )
        assert profile.session_id == "EXPERT01"
        assert profile.is_active

    def test_get_active_profile(self, db, test_user, test_procedure):
        save_expert_profile(db, "EXP02", test_procedure.id, test_user.id, [], {}, 20.0)
        p = get_active_expert_profile(db, test_procedure.id)
        assert p is not None
        assert p.is_active

    def test_new_profile_deactivates_old(self, db, test_user, test_procedure):
        save_expert_profile(db, "EXP03a", test_procedure.id, test_user.id, [], {}, 20.0)
        save_expert_profile(db, "EXP03b", test_procedure.id, test_user.id, [], {}, 22.0)
        active = get_active_expert_profile(db, test_procedure.id)
        assert active.session_id == "EXP03b"
