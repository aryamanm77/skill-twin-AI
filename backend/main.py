"""FastAPI application entry point."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.database.db import init_db
from app.api.routes import auth, procedures, sessions, calibration
from app.api.websocket import router as ws_router
from app.hardware.esp32 import get_esp32


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    print("✓ Database initialized")
    esp32 = get_esp32()
    print(f"✓ ESP32: {'connected' if esp32.is_connected else 'simulation mode'}")
    yield
    # Shutdown
    from app.vision.pipeline import get_pipeline
    pipeline = get_pipeline()
    if pipeline.is_running:
        pipeline.stop_session()
    print("👋 Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Practical Skill Training & Assessment Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(procedures.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(calibration.router, prefix="/api")
app.include_router(ws_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "privacy": "LOCAL_PROCESSING_RAW_VIDEO_NOT_STORED",
    }


@app.get("/api/status")
def status():
    from app.vision.pipeline import get_pipeline
    from app.vision.detector import get_detector
    from app.api.ws_manager import manager
    pipeline = get_pipeline()
    detector = get_detector()
    return {
        "pipeline": pipeline.get_status(),
        "model_status": detector.model_status,
        "ws_clients": manager.connected_count,
        "privacy": {
            "raw_video_stored": settings.STORE_RAW_VIDEO,
            "face_recognition": False,
            "processing": "local",
        }
    }


@app.get("/api/camera/modes")
def camera_modes():
    return {
        "modes": [
            {"id": "test", "name": "TEST MODE (Simulation)", "description": "Synthetic data — no real camera needed"},
            {"id": "real", "name": "Real Webcam", "description": "Uses laptop/external webcam"},
            {"id": "video", "name": "Video File", "description": "Upload an MP4/AVI file"},
        ]
    }
