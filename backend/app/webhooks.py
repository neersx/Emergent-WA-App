"""Webhook ingestion endpoint.

Critical correctness rules:
1. ALWAYS verify the HMAC-SHA256 signature with META_APP_SECRET before doing anything.
2. ACK in <1s: only write the raw payload + enqueue a job. NO heavy processing.
3. Use the raw request body bytes for signature verification (json reserialization
   would change the digest).
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from loguru import logger

from .config import settings
from .db import get_db
from .meta_client import verify_signature
from .queue import enqueue

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("/meta")
async def verify_challenge(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
):
    """GET verification handshake from Meta."""
    if hub_mode == "subscribe" and hub_verify_token == settings.META_WEBHOOK_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verify token")


@router.post("/meta")
async def ingest(request: Request):
    """Ingest a webhook event: verify, persist raw, enqueue, ACK fast."""
    started = time.perf_counter()

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256") or request.headers.get(
        "x-hub-signature-256"
    )

    if not verify_signature(body, signature):
        # We deliberately do NOT enqueue or persist anything for invalid signatures.
        logger.warning("Webhook signature verification FAILED")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except Exception:
        payload = {"_raw": body.decode("utf-8", errors="replace")}

    event_id = str(uuid.uuid4())
    raw_doc = {
        "_id": event_id,
        "payload": payload,
        "signature_ok": True,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "processed_at": None,
        "status": "received",
    }
    await get_db().webhook_events_raw.insert_one(raw_doc)
    await enqueue("process_webhook", {"event_id": event_id})

    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(f"Webhook ACK in {elapsed_ms:.1f}ms id={event_id}")
    return {"received": True, "id": event_id, "ack_ms": round(elapsed_ms, 2)}
