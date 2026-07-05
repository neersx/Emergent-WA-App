"""Background worker: processes webhook events + periodic template sync + usage rollup.

Job types:
  process_webhook          – project a raw webhook event into messages/conversations
  process_template_webhook – handle message_template_status_update webhook change
  sync_templates_waba      – pull current templates from Meta for a single WABA

Periodic tasks (run in worker loop):
  - Template sync: every TEMPLATE_SYNC_INTERVAL seconds
  - Daily usage rollup: incremental on each delivered message (no separate job needed)
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from loguru import logger

from .config import settings
from .db import get_db
from .media import download_and_store, make_media_url
from .queue import claim_one, complete, fail

_worker_task: asyncio.Task | None = None
_stop = asyncio.Event()

TEMPLATE_SYNC_INTERVAL = 600  # 10 minutes
_last_template_sync = 0.0

APP_BASE_URL = settings.__class__.__dict__.get("APP_URL", "")


def _get_app_url() -> str:
    import os
    return os.environ.get("APP_URL", "")


# ─── Message type extraction ─────────────────────────────────────────────────

def _extract_message_content(msg: dict) -> dict:
    """Normalize all WhatsApp message types into a flat dict for storage."""
    msg_type = msg.get("type", "unknown")
    content: dict[str, Any] = {
        "msg_type": msg_type,
        "body": None,
        "media_id": None,
        "mime_type": None,
        "caption": None,
        "filename": None,
        "latitude": None,
        "longitude": None,
        "location_name": None,
        "location_address": None,
        "contact_name": None,
        "interactive_type": None,
        "interactive_reply_id": None,
        "interactive_reply_title": None,
        "reaction_message_id": None,
        "reaction_emoji": None,
        "referral_source_type": None,
    }

    if msg_type == "text":
        content["body"] = (msg.get("text") or {}).get("body")

    elif msg_type in ("image", "video", "audio", "sticker"):
        sub = msg.get(msg_type) or {}
        content["media_id"] = sub.get("id")
        content["mime_type"] = sub.get("mime_type")
        content["caption"] = sub.get("caption")

    elif msg_type == "document":
        sub = msg.get("document") or {}
        content["media_id"] = sub.get("id")
        content["mime_type"] = sub.get("mime_type")
        content["filename"] = sub.get("filename")
        content["caption"] = sub.get("caption")

    elif msg_type == "location":
        loc = msg.get("location") or {}
        content["latitude"] = loc.get("latitude")
        content["longitude"] = loc.get("longitude")
        content["location_name"] = loc.get("name")
        content["location_address"] = loc.get("address")

    elif msg_type == "contacts":
        contacts = msg.get("contacts") or [{}]
        name = (contacts[0].get("name") or {}).get("formatted_name") or "Contact"
        content["contact_name"] = name
        content["body"] = name

    elif msg_type == "interactive":
        inter = msg.get("interactive") or {}
        content["interactive_type"] = inter.get("type")
        if inter.get("type") == "button_reply":
            r = inter.get("button_reply") or {}
            content["interactive_reply_id"] = r.get("id")
            content["interactive_reply_title"] = r.get("title")
            content["body"] = r.get("title")
        elif inter.get("type") == "list_reply":
            r = inter.get("list_reply") or {}
            content["interactive_reply_id"] = r.get("id")
            content["interactive_reply_title"] = r.get("title")
            content["body"] = r.get("title")

    elif msg_type == "reaction":
        reaction = msg.get("reaction") or {}
        content["reaction_message_id"] = reaction.get("message_id")
        content["reaction_emoji"] = reaction.get("emoji")
        content["body"] = f"Reacted with {reaction.get('emoji', '?')}"

    # Free-entry-point detection (Click-to-WhatsApp / CTA ad referral)
    referral = msg.get("referral") or {}
    if referral.get("source_type") in ("ad", "post", "click_to_wa"):
        content["referral_source_type"] = referral.get("source_type")

    return content


# ─── Cost + usage rollup ─────────────────────────────────────────────────────

def _is_billable(
    pricing_category: str,
    billable_from_webhook: bool | None,
    service_window_open: bool,
    free_entry_point: bool,
) -> bool:
    if free_entry_point:
        return False
    if billable_from_webhook is not None:
        return billable_from_webhook
    cat = (pricing_category or "service").lower()
    if cat == "marketing":
        return True
    if cat == "authentication":
        return True
    if cat == "utility":
        return not service_window_open
    return not service_window_open  # service/free-form


_COST_TABLE: dict[str, float] = {
    "marketing": 0.025,
    "utility": 0.015,
    "authentication": 0.015,
    "service": 0.0,
}


def _estimate_cost(category: str, billable: bool) -> float:
    if not billable:
        return 0.0
    return _COST_TABLE.get((category or "service").lower(), 0.01)


async def _update_usage_rollup(
    tenant_id: str,
    day: str,
    category: str,
    country_code: str | None,
    billable: bool,
    cost: float,
) -> None:
    key = f"{tenant_id}:{day}:{category}:{country_code or 'UNKNOWN'}"
    now = datetime.now(timezone.utc).isoformat()
    await get_db().usage_daily_rollup.update_one(
        {"_id": key},
        {
            "$inc": {
                "delivered_count": 1,
                "billable_count": 1 if billable else 0,
                "free_count": 0 if billable else 1,
                "cost_amount": cost,
            },
            "$setOnInsert": {
                "_id": key,
                "tenant_id": tenant_id,
                "day": day,
                "category": category,
                "country_code": country_code,
                "cost_currency": "USD",
                "created_at": now,
            },
            "$set": {"updated_at": now},
        },
        upsert=True,
    )


# ─── Service window helpers ───────────────────────────────────────────────────

def _window_open(last_inbound_iso: str | None, hours: int = 24) -> bool:
    if not last_inbound_iso:
        return False
    try:
        dt = datetime.fromisoformat(last_inbound_iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt) < timedelta(hours=hours)
    except Exception:
        return False


# ─── Core webhook projector ───────────────────────────────────────────────────

async def _project_webhook(event_id: str) -> None:
    db = get_db()
    raw = await db.webhook_events_raw.find_one({"_id": event_id})
    if not raw:
        logger.warning(f"Webhook event {event_id} not found")
        return

    payload = raw.get("payload") or {}
    now_iso = datetime.now(timezone.utc).isoformat()

    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            field = change.get("field", "")
            value = change.get("value") or {}

            # ── Template status updates ──────────────────────────────────────
            if field == "message_template_status_update":
                await _handle_template_status_change(value)
                continue

            if field != "messages":
                continue

            phone_number_id = (value.get("metadata") or {}).get("phone_number_id")

            # ── Outbound status updates ──────────────────────────────────────
            for st in value.get("statuses", []) or []:
                await _handle_status_update(st, phone_number_id, now_iso)

            # ── Inbound messages ─────────────────────────────────────────────
            for msg in value.get("messages", []) or []:
                await _handle_inbound_message(msg, phone_number_id, now_iso)

    await db.webhook_events_raw.update_one(
        {"_id": event_id},
        {"$set": {"processed_at": now_iso, "status": "processed"}},
    )


async def _handle_status_update(
    st: dict, phone_number_id: str | None, now_iso: str
) -> None:
    db = get_db()
    meta_message_id = st.get("id")
    status_name = st.get("status")  # sent | delivered | read | failed
    if not meta_message_id or not status_name:
        return

    ts_field = {
        "sent": "sent_at",
        "delivered": "delivered_at",
        "read": "read_at",
        "failed": "failed_at",
    }.get(status_name)

    update: dict[str, Any] = {"status": status_name, "updated_at": now_iso}
    if ts_field:
        update[ts_field] = now_iso

    # Pricing / cost capture
    pricing = st.get("pricing") or {}
    pricing_category = pricing.get("category") or "service"
    billable_raw = pricing.get("billable")
    conversation_info = st.get("conversation") or {}
    origin_type = (conversation_info.get("origin") or {}).get("type") or pricing_category

    if pricing:
        update["pricing_category"] = pricing_category
        update["pricing_billable"] = billable_raw

    if st.get("errors"):
        update["error"] = ((st.get("errors") or [{}])[0] or {}).get("title")
        update["error_code"] = ((st.get("errors") or [{}])[0] or {}).get("code")

    # Update message
    msg_doc = await db.messages.find_one_and_update(
        {"meta_message_id": meta_message_id},
        {"$set": update},
        return_document=True,
    )

    # On delivery: update cost rollup + broadcast WS update
    if msg_doc and status_name == "delivered":
        tenant_id = msg_doc.get("tenant_id")
        conv_doc = await db.conversations.find_one(
            {"id": msg_doc.get("conversation_id")}
        ) if msg_doc.get("conversation_id") else None
        service_window = _window_open(
            (conv_doc or {}).get("last_inbound_at")
        )
        free_entry = bool((conv_doc or {}).get("free_entry_point_expires_at") and
                          _window_open((conv_doc or {}).get("free_entry_point_expires_at"), hours=0))

        billable = _is_billable(origin_type, billable_raw, service_window, free_entry)
        cost = _estimate_cost(origin_type, billable)
        day = now_iso[:10]

        if tenant_id:
            await _update_usage_rollup(
                tenant_id, day, origin_type, None, billable, cost
            )
            # WS broadcast
            from .ws import ws_manager
            await ws_manager.broadcast(tenant_id, {
                "type": "status_update",
                "message_id": msg_doc.get("id") or msg_doc.get("_id"),
                "meta_message_id": meta_message_id,
                "status": status_name,
            })


async def _handle_inbound_message(
    msg: dict, phone_number_id: str | None, now_iso: str
) -> None:
    db = get_db()
    from_wa_id = msg.get("from")
    meta_message_id = msg.get("id")
    if not from_wa_id or not phone_number_id:
        return

    # Resolve tenant
    phone_doc = await db.phone_numbers.find_one({"phone_number_id": phone_number_id})
    if not phone_doc:
        return
    tenant_id = phone_doc["tenant_id"]

    # Free entry point (72h window for click-to-WA / ads)
    content = _extract_message_content(msg)
    is_free_entry = bool(content.get("referral_source_type"))

    # Upsert conversation + bump service window
    conv_id = f"conv_{phone_number_id}_{from_wa_id}"
    conv_update: dict[str, Any] = {
        "last_inbound_at": now_iso,
        "updated_at": now_iso,
    }
    if is_free_entry:
        free_expires = (
            datetime.now(timezone.utc) + timedelta(hours=72)
        ).isoformat()
        conv_update["free_entry_point_expires_at"] = free_expires

    conv = await db.conversations.find_one_and_update(
        {
            "tenant_id": tenant_id,
            "phone_number_id": phone_number_id,
            "contact_wa_id": from_wa_id,
        },
        {
            "$set": conv_update,
            "$setOnInsert": {
                "_id": conv_id,
                "id": conv_id,
                "tenant_id": tenant_id,
                "phone_number_id": phone_number_id,
                "contact_wa_id": from_wa_id,
                "status": "open",
                "assigned_to": None,
                "unread_count": 0,
                "created_at": now_iso,
            },
        },
        upsert=True,
        return_document=True,
    )
    # Increment unread
    await db.conversations.update_one(
        {"id": conv_id}, {"$inc": {"unread_count": 1}}
    )

    # Persist inbound message
    mid = str(uuid.uuid4())
    record: dict[str, Any] = {
        "_id": mid,
        "id": mid,
        "tenant_id": tenant_id,
        "phone_number_id": phone_number_id,
        "conversation_id": conv_id,
        "direction": "inbound",
        "from_wa_id": from_wa_id,
        "meta_message_id": meta_message_id,
        "status": "delivered",
        "created_at": now_iso,
        **content,
    }
    await db.messages.insert_one(record)

    # Download media in background (don't await - fire & forget)
    if content.get("media_id") and not settings.META_MOCK_MODE:
        asyncio.create_task(
            _download_message_media(
                tenant_id=tenant_id,
                message_id=mid,
                media_id=content["media_id"],
                mime_type=content.get("mime_type") or "application/octet-stream",
                waba_id=phone_doc["waba_id"],
                api_version=settings.META_GRAPH_API_VERSION,
            )
        )

    # WebSocket broadcast
    from .ws import ws_manager
    # Build a serializable message snapshot
    msg_payload = {k: v for k, v in record.items() if k not in ("_id",)}
    await ws_manager.broadcast(tenant_id, {
        "type": "new_message",
        "conversation_id": conv_id,
        "message": msg_payload,
    })


async def _download_message_media(
    tenant_id: str,
    message_id: str,
    media_id: str,
    mime_type: str,
    waba_id: str,
    api_version: str,
) -> None:
    from .crypto_utils import decrypt
    db = get_db()
    cred = await db.waba_credentials.find_one({"waba_id": waba_id})
    if not cred:
        return
    token = decrypt(cred["encrypted_business_token"])
    local_path, ext = await download_and_store(
        media_id=media_id,
        tenant_id=tenant_id,
        business_token=token,
        mime_type=mime_type,
        api_version=api_version,
    )
    if local_path:
        app_url = _get_app_url()
        media_url = make_media_url(app_url, tenant_id, media_id, ext) if app_url else None
        await db.messages.update_one(
            {"_id": message_id},
            {"$set": {"media_url": media_url, "media_local_path": local_path}},
        )


# ─── Template status webhook handler ─────────────────────────────────────────

async def _handle_template_status_change(value: dict) -> None:
    from .templates import apply_template_status_update
    from .ws import ws_manager

    db = get_db()
    event = value.get("event", "")  # APPROVED | REJECTED | PAUSED | DISABLED
    name = value.get("message_template_name", "")
    language = value.get("message_template_language", "")
    reason = value.get("reason")
    waba_id_hint = str(value.get("waba_id") or "")

    await apply_template_status_update(
        waba_id=waba_id_hint,
        template_name=name,
        language=language,
        new_status=event,
        reason=reason,
    )

    # Broadcast to all tenants owning this WABA
    waba_docs = await db.wabas.find({"waba_id": waba_id_hint}).to_list(10)
    for waba_doc in waba_docs:
        await ws_manager.broadcast(waba_doc["tenant_id"], {
            "type": "template_update",
            "template_name": name,
            "waba_id": waba_id_hint,
            "status": event,
            "reason": reason,
        })


# ─── Periodic template sync ───────────────────────────────────────────────────

async def _schedule_template_sync() -> None:
    """Enqueue sync jobs for all WABAs that haven't been synced recently."""
    from .queue import enqueue
    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=TEMPLATE_SYNC_INTERVAL)).isoformat()
    wabas = await db.wabas.find(
        {
            "$or": [
                {"templates_last_synced_at": {"$lt": cutoff}},
                {"templates_last_synced_at": {"$exists": False}},
            ]
        }
    ).to_list(100)
    for w in wabas:
        await enqueue("sync_templates_waba", {
            "waba_id": w["waba_id"],
            "tenant_id": w["tenant_id"],
        })


async def _sync_templates_for_waba(waba_id: str, tenant_id: str) -> None:
    from .crypto_utils import decrypt
    from .meta_client import meta_client
    db = get_db()
    cred = await db.waba_credentials.find_one({"waba_id": waba_id})
    token = decrypt(cred["encrypted_business_token"]) if cred else ""
    fetched = await meta_client.list_templates(waba_id, token)
    now = datetime.now(timezone.utc).isoformat()
    for t in fetched:
        key = {
            "tenant_id": tenant_id,
            "waba_id": waba_id,
            "name": t["name"],
            "language": t.get("language", "en_US"),
        }
        await db.templates.update_one(
            key,
            {
                "$set": {
                    **key,
                    "category": t.get("category"),
                    "body": t.get("body"),
                    "components": t.get("components") or [],
                    "status": t.get("status", "APPROVED"),
                    "meta_template_id": t.get("meta_template_id"),
                    "rejection_reason": t.get("rejection_reason"),
                    "updated_at": now,
                    "source": "meta",
                },
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "id": str(uuid.uuid4()),
                    "created_at": now,
                },
            },
            upsert=True,
        )
    await db.wabas.update_one(
        {"waba_id": waba_id}, {"$set": {"templates_last_synced_at": now}}
    )
    logger.info(f"Periodic sync: {len(fetched)} templates waba={waba_id}")


# ─── Job dispatcher ───────────────────────────────────────────────────────────

async def _handle_job(job: dict) -> None:
    jtype = job["type"]
    payload = job.get("payload") or {}
    if jtype == "process_webhook":
        await _project_webhook(payload["event_id"])
    elif jtype == "sync_templates_waba":
        await _sync_templates_for_waba(
            waba_id=payload["waba_id"],
            tenant_id=payload["tenant_id"],
        )
    else:
        raise ValueError(f"Unknown job type: {jtype}")


# ─── Worker loop ──────────────────────────────────────────────────────────────

async def worker_loop() -> None:
    global _last_template_sync
    poll_seconds = settings.WORKER_POLL_INTERVAL_MS / 1000
    logger.info(f"Worker started (poll={poll_seconds}s)")
    while not _stop.is_set():
        try:
            # Periodic template sync check
            now_ts = time.time()
            if now_ts - _last_template_sync > TEMPLATE_SYNC_INTERVAL:
                _last_template_sync = now_ts
                try:
                    await _schedule_template_sync()
                except Exception as exc:
                    logger.warning(f"Template sync scheduling failed: {exc}")

            job = await claim_one()
            if not job:
                await asyncio.sleep(poll_seconds)
                continue
            try:
                await _handle_job(job)
                await complete(job["_id"])
            except Exception as exc:
                logger.exception(f"Job {job['_id']} failed: {exc}")
                await fail(job["_id"], str(exc))
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception(f"Worker loop error: {exc}")
            await asyncio.sleep(1.0)
    logger.info("Worker stopped")


def start_worker(loop: asyncio.AbstractEventLoop | None = None) -> None:
    global _worker_task
    if not settings.WORKER_ENABLED:
        logger.info("Worker disabled via WORKER_ENABLED=false")
        return
    if _worker_task and not _worker_task.done():
        return
    _stop.clear()
    _worker_task = asyncio.create_task(worker_loop(), name="meta-webhook-worker")


async def stop_worker() -> None:
    global _worker_task
    _stop.set()
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except Exception:
            pass
        _worker_task = None
