"""SkillTwin AI - Core Configuration"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SkillTwin AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: list = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    # Security
    SECRET_KEY: str = "skilltwin-dev-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/skilltwin.db"

    # Vision
    CAMERA_INDEX: int = 0
    CAMERA_WIDTH: int = 1280
    CAMERA_HEIGHT: int = 720
    CAMERA_FPS: int = 30
    YOLO_MODEL: str = "yolov8n.pt"
    YOLO_CONFIDENCE: float = 0.45
    TRACKER_CONFIG: str = "bytetrack.yaml"

    # ESP32
    ESP32_PORT: str = ""
    ESP32_BAUD: int = 115200
    ESP32_ENABLED: bool = False

    # Privacy
    STORE_RAW_VIDEO: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
