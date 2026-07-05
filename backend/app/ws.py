"""WebSocket connection manager for real-time inbox + template updates."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import APIRouter, Cookie, WebSocket, WebSocketDisconnect
from loguru import logger

from .auth import decode_access_token
from .models import Role

router = APIRouter()


class ConnectionManager:
    """In-process tenant-scoped broadcaster. One process → no pub/sub needed."""

    def __init__(self) -> None:
        self._conns: dict[str, set[WebSocket]] = defaultdict(set)

    def add(self, tenant_id: str, ws: WebSocket) -> None:
        self._conns[tenant_id].add(ws)

    def remove(self, tenant_id: str, ws: WebSocket) -> None:
        self._conns[tenant_id].discard(ws)

    async def broadcast(self, tenant_id: str, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._conns.get(tenant_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._conns[tenant_id].discard(ws)

    def count(self, tenant_id: str) -> int:
        return len(self._conns.get(tenant_id, set()))


ws_manager = ConnectionManager()


@router.websocket("/api/ws/inbox")
async def inbox_websocket(
    websocket: WebSocket,
    access_token: str | None = Cookie(default=None),
) -> None:
    """Real-time inbox WebSocket.

    Auth: reads the httpOnly `access_token` cookie automatically sent by the
    browser during the WS handshake (same-origin). Closes 4001 if invalid.

    Server → client events:
      {"type":"new_message",  "conversation_id":"…", "message":{…}}
      {"type":"status_update","message_id":"…",       "status":"delivered"}
      {"type":"template_update","template_name":"…","waba_id":"…",
       "status":"APPROVED","reason":null}
      {"type":"conversation_update","conversation":{…}}
      {"type":"ping"}

    Client → server: text frame "ping"  →  server replies "pong"
    """
    await websocket.accept()
    tenant_id: str | None = None
    try:
        if not access_token:
            await websocket.send_json({"type": "auth_failed", "reason": "no_cookie"})
            await websocket.close(code=4001)
            return

        try:
            payload = decode_access_token(access_token)
            if payload.get("typ") != "access":
                raise ValueError("not access")
            tenant_id = payload.get("tenant_id")
            if not tenant_id:
                raise ValueError("no tenant")
        except Exception as exc:
            await websocket.send_json({"type": "auth_failed", "reason": str(exc)})
            await websocket.close(code=4001)
            return

        ws_manager.add(tenant_id, websocket)
        await websocket.send_json({"type": "auth_ok", "tenant_id": tenant_id})
        logger.info(f"[ws] +connect tenant={tenant_id} total={ws_manager.count(tenant_id)}")

        while True:
            try:
                text = await asyncio.wait_for(websocket.receive_text(), timeout=35)
                if text == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug(f"[ws] error: {exc}")
    finally:
        if tenant_id:
            ws_manager.remove(tenant_id, websocket)
            logger.info(f"[ws] -disconnect tenant={tenant_id} remaining={ws_manager.count(tenant_id)}")
