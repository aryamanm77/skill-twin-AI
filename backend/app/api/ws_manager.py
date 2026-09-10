"""
WebSocket connection manager and message broadcasting.
"""
import json
import asyncio
import time
from typing import Dict, List, Optional, Any
from fastapi import WebSocket
from app.core.config import settings


class WSMessage:
    """Standard WebSocket message format."""

    @staticmethod
    def detection(frame_data: dict, tracked: list, is_test: bool) -> dict:
        return {
            "type": "detection",
            "timestamp": time.time(),
            "test_mode": is_test,
            "data": {
                "tracked_objects": tracked,
                "model_status": frame_data.get("model_status", "ok"),
                "inference_ms": frame_data.get("inference_ms", 0),
            }
        }

    @staticmethod
    def step_event(event: dict) -> dict:
        return {"type": "step_event", "timestamp": time.time(), "data": event}

    @staticmethod
    def score_update(score: dict) -> dict:
        return {"type": "score_update", "timestamp": time.time(), "data": score}

    @staticmethod
    def feedback(message: str, severity: str = "info", event_type: str = "info") -> dict:
        return {
            "type": "feedback",
            "timestamp": time.time(),
            "data": {"message": message, "severity": severity, "event_type": event_type}
        }

    @staticmethod
    def fsm_state(state: dict) -> dict:
        return {"type": "fsm_state", "timestamp": time.time(), "data": state}

    @staticmethod
    def session_status(status: str, session_id: str, mode: str) -> dict:
        return {
            "type": "session_status", "timestamp": time.time(),
            "data": {"status": status, "session_id": session_id, "mode": mode}
        }

    @staticmethod
    def error(message: str, code: str = "error") -> dict:
        return {
            "type": "error", "timestamp": time.time(),
            "data": {"message": message, "code": code}
        }

    @staticmethod
    def video_frame(jpeg_b64: str, width: int, height: int, test_mode: bool) -> dict:
        return {
            "type": "video_frame", "timestamp": time.time(),
            "data": {"frame": jpeg_b64, "width": width, "height": height, "test_mode": test_mode}
        }


class ConnectionManager:
    """Manages active WebSocket connections with broadcast support."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[client_id] = ws

    def disconnect(self, client_id: str):
        self._connections.pop(client_id, None)

    async def send(self, client_id: str, message: dict):
        ws = self._connections.get(client_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, message: dict):
        dead = []
        for cid, ws in self._connections.items():
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.disconnect(cid)

    @property
    def connected_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()
