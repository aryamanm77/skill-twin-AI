"""
WebSocket endpoint for real-time pipeline data streaming.
"""
import uuid
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.ws_manager import manager, WSMessage

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    client_id = str(uuid.uuid4())[:8]
    await manager.connect(client_id, ws)
    try:
        # Send initial connection ack
        await manager.send(client_id, {
            "type": "connected",
            "client_id": client_id,
            "message": "SkillTwin AI WebSocket connected",
        })
        # Keep alive: handle any incoming messages
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30)
                # Handle ping
                if data == "ping":
                    await manager.send(client_id, {"type": "pong"})
            except asyncio.TimeoutError:
                # Send keepalive
                await manager.send(client_id, {"type": "keepalive"})
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception:
        manager.disconnect(client_id)
