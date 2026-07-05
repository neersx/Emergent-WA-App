"""Conversation inbox + service window tracking + agent assignment.

A conversation = (tenant_id, phone_number_id, contact_wa_id).

Phase 2 additions:
- Agent assignment / close / reopen
- All message types serialized with media URLs
- Unread count reset on thread open
- Free-entry-point (72h) window exposed
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from .crypto_utils import decrypt
from .db import get_db
from .media import make_media_url
from .meta_client import meta_client
from .models import AssignConversationRequest, CloseConversationRequest
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api/inbox", tags=["inbox"])

SERVICE_WINDOW_HOURS = 24
FREE_ENTRY_HOURS = 72
APP_URL = os.environ.get("APP_URL", "")


class ReplyRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4096)
    idempotency_key: str | None = Field(default=None, max_length=120)


class SimulateInboundRequest(BaseModel):
    contact_wa_id: str = Field(default="15559998888", min_length=5, max_length=32)
    body: str = Field(default="Hi! I have a question about my order.", min_length=1, max_length=2048)
    phone_number_id: str | None = None


# ─── Window helpers ───────────────────────────────────────────────────────────

def _in_window(conv: dict, hours: int = SERVICE_WINDOW_HOURS) -> bool:
    last = conv.get("last_inbound_at")
    if not last:
        return False
    try:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt) < timedelta(hours=hours)
    except Exception:
        return False


def _window_expires(iso: str, hours: int) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (dt + timedelta(hours=hours)).isoformat()


def _in_free_entry(conv: dict) -> bool:
    exp = conv.get("free_entry_point_expires_at")
    if not exp:
        return False
    try:
        return datetime.now(timezone.utc) < datetime.fromisoformat(exp.replace("Z", "+00:00"))
    except Exception:
        return False


# ─── Message serializer ────────────────────────────────────────────────────────

def _serialize_message(m: dict) -> dict:
    media_url = m.get("media_url")
    # Generate a fresh signed URL if we have a media_id but no URL yet
    if not media_url and m.get("media_id") and APP_URL:
        from .media import mime_to_ext
        ext = mime_to_ext(m.get("mime_type"))
        media_url = make_media_url(APP_URL, m.get("tenant_id", ""), m["media_id"], ext)

    return {
        "id": m.get("id") or m.get("_id"),
        "direction": m.get("direction"),
        "msg_type": m.get("msg_type", "text"),
        "body": m.get("body"),
        "to_wa_id": m.get("to_wa_id"),
        "from_wa_id": m.get("from_wa_id"),
        "template_name": m.get("template_name"),
        "is_template": bool(m.get("template_name")) and not m.get("body"),
        # Media
        "media_id": m.get("media_id"),
        "media_url": media_url,
        "mime_type": m.get("mime_type"),
        "caption": m.get("caption"),
        "filename": m.get("filename"),
        # Location
        "latitude": m.get("latitude"),
        "longitude": m.get("longitude"),
        "location_name": m.get("location_name"),
        "location_address": m.get("location_address"),
        # Contacts
        "contact_name": m.get("contact_name"),
        # Interactive
        "interactive_type": m.get("interactive_type"),
        "interactive_reply_id": m.get("interactive_reply_id"),
        "interactive_reply_title": m.get("interactive_reply_title"),
        # Reaction
        "reaction_emoji": m.get("reaction_emoji"),
        "reaction_message_id": m.get("reaction_message_id"),
        # Status
        "status": m.get("status"),
        "error": m.get("error"),
        "created_at": m.get("created_at"),
        "sent_at": m.get("sent_at"),
        "delivered_at": m.get("delivered_at"),
        "read_at": m.get("read_at"),
    }


def _serialize_conv(c: dict, last_msg: dict | None = None) -> dict:
    last_inbound = c.get("last_inbound_at")
    return {
        "id": c["id"],
        "phone_number_id": c["phone_number_id"],
        "contact_wa_id": c["contact_wa_id"],
        "contact_name": c.get("contact_name"),
        "status": c.get("status", "open"),
        "assigned_to": c.get("assigned_to"),
        "unread_count": c.get("unread_count", 0),
        "last_inbound_at": last_inbound,
        "service_window_open": _in_window(c),
        "service_window_expires_at": (
            _window_expires(last_inbound, SERVICE_WINDOW_HOURS) if last_inbound else None
        ),
        "free_entry_point": _in_free_entry(c),
        "free_entry_point_expires_at": c.get("free_entry_point_expires_at"),
        "last_message_preview": (
            (_serialize_message(last_msg).get("body") or
             last_msg.get("msg_type") or
             last_msg.get("template_name") or "")[:80]
            if last_msg else ""
        ),
        "last_message_direction": last_msg.get("direction") if last_msg else None,
        "last_message_at": last_msg.get("created_at") if last_msg else c.get("created_at"),
        "created_at": c.get("created_at"),
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(
    p: Principal = Depends(require_tenant),
    limit: int = Query(50, le=200),
    status: str | None = Query(default=None),
    phone_number_id: str | None = Query(default=None),
):
    db = get_db()
    filt: dict = {"tenant_id": p.tenant_id}
    if status:
        filt["status"] = status
    if phone_number_id:
        filt["phone_number_id"] = phone_number_id

    docs = (
        await db.conversations.find(filt)
        .sort("last_inbound_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    out = []
    for c in docs:
        last_msg = await db.messages.find_one(
            {"tenant_id": p.tenant_id, "conversation_id": c["id"]},
            sort=[("created_at", -1)],
        )
        out.append(_serialize_conv(c, last_msg))
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

    # Reset unread count on thread open
    await db.conversations.update_one(
        {"id": conversation_id}, {"$set": {"unread_count": 0}}
    )

    last_inbound = conv.get("last_inbound_at")
    return {
        "conversation": {
            "id": conv["id"],
            "contact_wa_id": conv["contact_wa_id"],
            "contact_name": conv.get("contact_name"),
            "phone_number_id": conv["phone_number_id"],
            "status": conv.get("status", "open"),
            "assigned_to": conv.get("assigned_to"),
            "service_window_open": _in_window(conv),
            "service_window_expires_at": (
                _window_expires(last_inbound, SERVICE_WINDOW_HOURS)
                if last_inbound else None
            ),
            "free_entry_point": _in_free_entry(conv),
            "free_entry_point_expires_at": conv.get("free_entry_point_expires_at"),
        },
        "messages": [_serialize_message(m) for m in msgs],
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

    # Window enforcement: 24h service window OR 72h free-entry window
    if not _in_window(conv) and not _in_free_entry(conv):
        raise HTTPException(
            status_code=409,
            detail=(
                "Service window closed. The customer hasn't messaged in the last 24h. "
                "Send an approved template to re-open the window."
            ),
        )
    if conv.get("status") == "closed":
        raise HTTPException(
            status_code=409,
            detail="Conversation is closed. Reopen it before replying."
        )

    if body.idempotency_key:
        existing = await db.messages.find_one(
            {"tenant_id": p.tenant_id, "idempotency_key": body.idempotency_key}
        )
        if existing:
            return _serialize_message(existing)

    phone_doc = await db.phone_numbers.find_one(
        {"phone_number_id": conv["phone_number_id"]}
    )
    cred = await db.waba_credentials.find_one(
        {"waba_id": (phone_doc or {}).get("waba_id", "")}
    )
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
        "msg_type": "text",
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
    return _serialize_message(record)


@router.post("/conversations/{conversation_id}/assign")
async def assign_conversation(
    conversation_id: str,
    body: AssignConversationRequest,
    p: Principal = Depends(require_tenant),
):
    db = get_db()
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": p.tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"assigned_to": body.user_id, "updated_at": now}},
    )
    return {"assigned_to": body.user_id}


@router.post("/conversations/{conversation_id}/close")
async def close_conversation(
    conversation_id: str,
    body: CloseConversationRequest,
    p: Principal = Depends(require_tenant),
):
    db = get_db()
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": p.tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"status": "closed", "closed_at": now, "close_reason": body.reason, "updated_at": now}},
    )
    return {"status": "closed"}


@router.post("/conversations/{conversation_id}/reopen")
async def reopen_conversation(
    conversation_id: str,
    p: Principal = Depends(require_tenant),
):
    db = get_db()
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": p.tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"status": "open", "updated_at": now}},
    )
    return {"status": "open"}


@router.post("/conversations/{conversation_id}/simulate-inbound")
async def simulate_inbound_existing(
    conversation_id: str,
    body: SimulateInboundRequest,
    p: Principal = Depends(require_tenant),
):
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
    from .ws import ws_manager
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conv_id = f"conv_{phone_number_id}_{contact_wa_id}"
    await db.conversations.update_one(
        {"id": conv_id, "tenant_id": tenant_id},
        {
            "$set": {"last_inbound_at": now, "updated_at": now},
            "$inc": {"unread_count": 1},
            "$setOnInsert": {
                "_id": conv_id,
                "id": conv_id,
                "tenant_id": tenant_id,
                "phone_number_id": phone_number_id,
                "contact_wa_id": contact_wa_id,
                "status": "open",
                "assigned_to": None,
                "created_at": now,
            },
        },
        upsert=True,
    )
    mid = str(uuid.uuid4())
    record = {
        "_id": mid,
        "id": mid,
        "tenant_id": tenant_id,
        "phone_number_id": phone_number_id,
        "conversation_id": conv_id,
        "direction": "inbound",
        "msg_type": "text",
        "from_wa_id": contact_wa_id,
        "body": body,
        "status": "delivered",
        "created_at": now,
        "meta_message_id": f"wamid.SIM_{mid[:12].upper()}",
    }
    await db.messages.insert_one(record)
    logger.info(f"Simulated inbound from {contact_wa_id} on {phone_number_id}")

    await ws_manager.broadcast(tenant_id, {
        "type": "new_message",
        "conversation_id": conv_id,
        "message": _serialize_message(record),
    })
    return {"conversation_id": conv_id, "created": True}
