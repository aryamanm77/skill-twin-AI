"""Database engine, session factory, and initialization."""
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings, CONFIG_DIR, DATA_DIR
from app.database.models import Base, Domain, Procedure, User, UserRole
from app.core.security import hash_password

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite only
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables and seed initial data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_domains(db)
        _seed_procedures(db)
        _seed_admin_user(db)
    finally:
        db.close()


def _seed_domains(db: Session):
    domains_file = CONFIG_DIR / "domains.json"
    if not domains_file.exists():
        return
    data = json.loads(domains_file.read_text())
    for d in data["domains"]:
        if not db.get(Domain, d["id"]):
            db.add(Domain(
                id=d["id"],
                name=d["name"],
                icon=d.get("icon", "🏭"),
                description=d.get("description", ""),
            ))
    db.commit()


def _seed_procedures(db: Session):
    proc_dir = CONFIG_DIR / "procedures"
    for proc_file in proc_dir.glob("*.json"):
        data = json.loads(proc_file.read_text())
        proc_id = data["id"]
        if not db.get(Procedure, proc_id):
            db.add(Procedure(
                id=proc_id,
                name=data["name"],
                description=data.get("description", ""),
                domain_id=data["domain"],
                version=data.get("version", "1.0"),
                config_json=data,
                scoring_weights=data.get("scoring_weights"),
            ))
    db.commit()


def _seed_admin_user(db: Session):
    from sqlalchemy import select
    stmt = select(User).where(User.username == "admin")
    if db.execute(stmt).scalar_one_or_none() is None:
        db.add(User(
            username="admin",
            email="admin@skilltwin.ai",
            full_name="Administrator",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
        ))
        db.add(User(
            username="expert",
            email="expert@skilltwin.ai",
            full_name="Demo Expert",
            hashed_password=hash_password("expert123"),
            role=UserRole.EXPERT,
        ))
        db.add(User(
            username="trainee",
            email="trainee@skilltwin.ai",
            full_name="Demo Trainee",
            hashed_password=hash_password("trainee123"),
            role=UserRole.TRAINEE,
        ))
        db.commit()
