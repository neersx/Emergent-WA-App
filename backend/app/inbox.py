"""Conversation inbox + service window tracking.

A conversation = (tenant_id, phone_number_id, contact_wa_id).
The service window is the 24h period since the contact's last inbound message;
free-form (non-template) replies are only allowed inside that window.

Endpoints:
  GET    /api/inbox/conversations                  list conversations
  GET    /api/inbox/conversations/{id}/messages    thread messages
  POST   /api/inbox/conversations/{id}/reply       send a session text reply (if in-window)
  POST   /api/inbox/conversations/{id}/simulate-inbound  demo: insert an inbound message + bump window
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from .crypto_utils import decrypt
from .db import get_db
from .meta_client import meta_client
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api/inbox", tags=["inbox"])

SERVICE_WINDOW_HOURS = 24


class ReplyRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4096)
    idempotency_key: str | None = Field(default=None, max_length=120)


class SimulateInboundRequest(BaseModel):
    contact_wa_id: str = Field(default="15559998888", min_length=5, max_length=32)
    body: str = Field(default="Hi! I have a question about my order.", min_length=1, max_length=2048)
    phone_number_id: str | None = None


def _in_window(conv: dict) -> bool:
    last = conv.get("last_inbound_at")
    if not last:
        return False
    try:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except Exception:
        return False
    return (datetime.now(timezone.utc) - dt) < timedelta(hours=SERVICE_WINDOW_HOURS)


def _service_window_expires_at(last_inbound_iso: str) -> str:
    dt = datetime.fromisoformat(last_inbound_iso.replace("Z", "+00:00"))
    return (dt + timedelta(hours=SERVICE_WINDOW_HOURS)).isoformat()


@router.get("/conversations")
async def list_conversations(
    p: Principal = Depends(require_tenant), limit: int = Query(50, le=200)
):
    db = get_db()
    docs = (
        await db.conversations.find({"tenant_id": p.tenant_id})
        .sort("last_inbound_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    out = []
    for c in docs:
        # Last message preview
        last_msg = await db.messages.find_one(
            {"tenant_id": p.tenant_id, "conversation_id": c["id"]},
            sort=[("created_at", -1)],
        )
        out.append(
            {
                "id": c["id"],
                "phone_number_id": c["phone_number_id"],
                "contact_wa_id": c["contact_wa_id"],
                "last_inbound_at": c.get("last_inbound_at"),
                "service_window_open": _in_window(c),
                "service_window_expires_at": (
                    _service_window_expires_at(c["last_inbound_at"])
                    if c.get("last_inbound_at")
                    else None
                ),
                "last_message_preview": (
                    (last_msg.get("body") or last_msg.get("template_name") or "")[:80]
                    if last_msg
                    else ""
                ),
                "last_message_direction": last_msg.get("direction") if last_msg else None,
                "last_message_at": last_msg.get("created_at") if last_msg else c.get("created_at"),
            }
        )
    return out


@router.get("/conversations/{conversation_id}/messages")
async def thread(
    conversation_id: str,
    p: Principal = Depends(require_tenant),
    limit: int = Query(200, le=500),
):
    db = get_db()
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": p.tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = (
        await db.messages.find(
            {"tenant_id": p.tenant_id, "conversation_id": conversation_id}
        )
        .sort("created_at", 1)
        .limit(limit)
        .to_list(limit)
    )
    out = []
    for m in msgs:
        out.append(
            {
                "id": m["_id"],
                "direction": m.get("direction"),
                "to_wa_id": m.get("to_wa_id"),
                "from_wa_id": m.get("from_wa_id"),
                "body": m.get("body") or m.get("template_name"),
                "is_template": bool(m.get("template_name")) and not m.get("body"),
                "status": m.get("status"),
                "created_at": m.get("created_at"),
                "sent_at": m.get("sent_at"),
                "delivered_at": m.get("delivered_at"),
                "read_at": m.get("read_at"),
            }
        )
    return {
        "conversation": {
            "id": conv["id"],
            "contact_wa_id": conv["contact_wa_id"],
            "phone_number_id": conv["phone_number_id"],
            "service_window_open": _in_window(conv),
            "service_window_expires_at": (
                _service_window_expires_at(conv["last_inbound_at"])
                if conv.get("last_inbound_at")
                else None
            ),
        },
        "messages": out,
    }


@router.post("/conversations/{conversation_id}/reply")
async def reply(
    conversation_id: str,
    body: ReplyRequest,
    p: Principal = Depends(require_tenant),
):
    db = get_db()
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": p.tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not _in_window(conv):
        raise HTTPException(
            status_code=409,
            detail=(
                "Service window closed. The customer hasn't messaged in the last 24h. "
                "Send an approved template to re-open the window."
            ),
        )

    # Idempotency
    if body.idempotency_key:
        existing = await db.messages.find_one(
            {"tenant_id": p.tenant_id, "idempotency_key": body.idempotency_key}
        )
        if existing:
            return _serialize_msg(existing)

    cred = await db.waba_credentials.find_one({"waba_id": (await db.phone_numbers.find_one({"phone_number_id": conv["phone_number_id"]}))["waba_id"]})
    token = decrypt(cred["encrypted_business_token"]) if cred else ""

    res = await meta_client.send_text(
        phone_number_id=conv["phone_number_id"],
        business_token=token,
        to_wa_id=conv["contact_wa_id"],
        text=body.body,
    )
    now = datetime.now(timezone.utc).isoformat()
    mid = str(uuid.uuid4())
    record = {
        "_id": mid,
        "id": mid,
        "tenant_id": p.tenant_id,
        "phone_number_id": conv["phone_number_id"],
        "conversation_id": conv["id"],
        "direction": "outbound",
        "to_wa_id": conv["contact_wa_id"],
        "body": body.body,
        "meta_message_id": res["messages"][0]["id"],
        "status": "sent",
        "created_at": now,
        "sent_at": now,
        "idempotency_key": body.idempotency_key,
    }
    await db.messages.insert_one(record)
    await db.conversations.update_one(
        {"id": conversation_id}, {"$set": {"updated_at": now}}
    )
    return _serialize_msg(record)


@router.post("/conversations/{conversation_id}/simulate-inbound")
async def simulate_inbound_existing(
    conversation_id: str,
    body: SimulateInboundRequest,
    p: Principal = Depends(require_tenant),
):
    """Demo helper: pretend the contact sent us a message. Bumps last_inbound_at."""
    db = get_db()
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": p.tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await _insert_simulated_inbound(
        tenant_id=p.tenant_id,
        phone_number_id=conv["phone_number_id"],
        contact_wa_id=conv["contact_wa_id"],
        body=body.body,
    )


@router.post("/simulate-inbound")
async def simulate_inbound_new(
    body: SimulateInboundRequest, p: Principal = Depends(require_tenant)
):
    """Demo helper: simulate an inbound message from a brand-new contact."""
    db = get_db()
    phone_number_id = body.phone_number_id
    if not phone_number_id:
        phone = await db.phone_numbers.find_one({"tenant_id": p.tenant_id})
        if not phone:
            raise HTTPException(
                status_code=400, detail="No phone numbers connected for this tenant"
            )
        phone_number_id = phone["phone_number_id"]
    else:
        phone = await db.phone_numbers.find_one(
            {"phone_number_id": phone_number_id, "tenant_id": p.tenant_id}
        )
        if not phone:
            raise HTTPException(status_code=404, detail="Phone not found")
    return await _insert_simulated_inbound(
        tenant_id=p.tenant_id,
        phone_number_id=phone_number_id,
        contact_wa_id=body.contact_wa_id,
        body=body.body,
    )


async def _insert_simulated_inbound(
    tenant_id: str, phone_number_id: str, contact_wa_id: str, body: str
):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conv_id = f"conv_{phone_number_id}_{contact_wa_id}"
    await db.conversations.update_one(
        {"id": conv_id, "tenant_id": tenant_id},
        {
            "$set": {"last_inbound_at": now, "updated_at": now},
            "$setOnInsert": {
                "_id": conv_id,
                "id": conv_id,
                "tenant_id": tenant_id,
                "phone_number_id": phone_number_id,
                "contact_wa_id": contact_wa_id,
                "created_at": now,
            },
        },
        upsert=True,
    )
    mid = str(uuid.uuid4())
    await db.messages.insert_one(
        {
            "_id": mid,
            "id": mid,
            "tenant_id": tenant_id,
            "phone_number_id": phone_number_id,
            "conversation_id": conv_id,
            "direction": "inbound",
            "from_wa_id": contact_wa_id,
            "body": body,
            "status": "delivered",
            "created_at": now,
            "meta_message_id": f"wamid.SIM_{mid[:12].upper()}",
        }
    )
    logger.info(f"Simulated inbound from {contact_wa_id} on {phone_number_id} (conv={conv_id})")
    return {"conversation_id": conv_id, "created": True}


def _serialize_msg(d: dict) -> dict:
    return {
        "id": d.get("_id") or d.get("id"),
        "direction": d.get("direction"),
        "to_wa_id": d.get("to_wa_id"),
        "from_wa_id": d.get("from_wa_id"),
        "body": d.get("body"),
        "status": d.get("status"),
        "created_at": d.get("created_at"),
        "sent_at": d.get("sent_at"),
    }
