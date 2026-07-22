"""WebSocket connection manager for real-time updates."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.core.auth import decode_access_token

logger = logging.getLogger("ai_content_os.websocket")

websocket_router = APIRouter()

VALID_CHANNELS = {"agent", "workflow", "content", "system"}


class ConnectionManager:
    """Manages WebSocket connections organized by channels."""

    def __init__(self):
        self._channels: Dict[str, Set[WebSocket]] = {}
        self._connections: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(websocket)
        self._connections.setdefault(websocket, set()).add(channel)
        logger.info("WebSocket connected to channel '%s'", channel)

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        if channel in self._channels:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                del self._channels[channel]
        if websocket in self._connections:
            self._connections[websocket].discard(channel)
            if not self._connections[websocket]:
                del self._connections[websocket]
        logger.info("WebSocket disconnected from channel '%s'", channel)

    async def broadcast(self, channel: str, message: dict) -> int:
        if channel not in self._channels:
            return 0

        payload = {
            "type": message.get("type", "broadcast"),
            "payload": message.get("payload", message),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(payload)
        disconnected: list[WebSocket] = []

        for ws in self._channels[channel]:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(data)
                else:
                    disconnected.append(ws)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            await self.disconnect(ws, channel)

        return len(self._channels.get(channel, set()))

    async def send_personal(self, websocket: WebSocket, message: dict) -> bool:
        payload = {
            "type": message.get("type", "personal"),
            "payload": message.get("payload", message),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(payload))
                return True
        except Exception:
            logger.exception("Failed to send personal WebSocket message")
        return False

    def get_channel_count(self, channel: str) -> int:
        return len(self._channels.get(channel, set()))

    def get_total_connections(self) -> int:
        return len(self._connections)

    def get_channel_stats(self) -> Dict[str, int]:
        return {ch: len(clients) for ch, clients in self._channels.items()}


manager = ConnectionManager()


@websocket_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str = Query(...),
    token: Optional[str] = Query(None),
):
    if channel not in VALID_CHANNELS:
        await websocket.close(code=4000, reason=f"Invalid channel: {channel}")
        return

    if token:
        payload = decode_access_token(token)
        if payload is None:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=4001, reason="Invalid token payload")
            return
    else:
        user_id = None

    await manager.connect(websocket, channel)

    await manager.send_personal(
        websocket,
        {
            "type": "connected",
            "payload": {
                "channel": channel,
                "user_id": user_id,
                "message": f"Connected to {channel} channel",
            },
        },
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket,
                    {
                        "type": "error",
                        "payload": {"message": "Invalid JSON"},
                    },
                )
                continue

            msg_type = data.get("type", "message")

            if msg_type == "ping":
                await manager.send_personal(
                    websocket,
                    {
                        "type": "pong",
                        "payload": {},
                    },
                )
            elif msg_type == "broadcast":
                count = await manager.broadcast(
                    channel,
                    {
                        "type": "message",
                        "payload": data.get("payload", {}),
                    },
                )
                await manager.send_personal(
                    websocket,
                    {
                        "type": "broadcast_sent",
                        "payload": {"channel": channel, "recipient_count": count},
                    },
                )
            else:
                await manager.broadcast(
                    channel,
                    {
                        "type": msg_type,
                        "payload": data.get("payload", data),
                    },
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception:
        logger.exception("WebSocket error on channel '%s'", channel)
        await manager.disconnect(websocket, channel)
