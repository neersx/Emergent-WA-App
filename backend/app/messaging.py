"""Outbound messaging endpoints + simulate-webhook admin helper.

Critical:
- Idempotency via `idempotency_keys` unique constraint (per tenant+key).
- Per phone_number rate limit using rate_limits collection (token bucket per minute).
- Tenant isolation: phone_number must belong to caller's tenant.
- Business token decrypted just before send; never returned.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pymongo.errors import DuplicateKeyError

from .config import settings
from .crypto_utils import decrypt
from .db import get_db
from .meta_client import meta_client, sign_payload
from .models import SendTemplateRequest, SimulateWebhookRequest, MessagePublic
from .queue import enqueue
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api/messages", tags=["messages"])


async def _check_rate_limit(phone_number_id: str) -> None:
    db = get_db()
    now = datetime.now(timezone.utc)
    window_start = now.replace(second=0, microsecond=0)
    doc = await db.rate_limits.find_one_and_update(
        {"phone_number_id": phone_number_id, "window_start": window_start.isoformat()},
        {"$inc": {"count": 1}, "$setOnInsert": {"created_at": now.isoformat()}},
        upsert=True,
        return_document=True,
    )
    if doc and doc.get("count", 0) > settings.SEND_RATE_LIMIT_PER_MIN:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for this phone number",
        )


@router.post("/send", response_model=MessagePublic)
async def send_template(
    body: SendTemplateRequest, p: Principal = Depends(require_tenant)
):
    db = get_db()

    # Verify phone belongs to tenant
    phone = await db.phone_numbers.find_one(
        {"phone_number_id": body.phone_number_id, "tenant_id": p.tenant_id}
    )
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")

    # Idempotency check
    if body.idempotency_key:
        try:
            await db.idempotency_keys.insert_one(
                {
                    "_id": f"{p.tenant_id}:{body.idempotency_key}",
                    "tenant_id": p.tenant_id,
                    "key": body.idempotency_key,
                    "created_at": datetime.now(timezone.utc),
                }
            )
        except DuplicateKeyError:
            existing = await db.messages.find_one(
                {"tenant_id": p.tenant_id, "idempotency_key": body.idempotency_key}
            )
            if existing:
                return _serialize_message(existing)
            raise HTTPException(status_code=409, detail="Duplicate idempotency key")

    await _check_rate_limit(body.phone_number_id)

    # Build queued message record
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    record = {
        "_id": msg_id,
        "id": msg_id,
        "tenant_id": p.tenant_id,
        "phone_number_id": body.phone_number_id,
        "direction": "outbound",
        "to_wa_id": body.to_wa_id,
        "template_name": body.template_name,
        "language_code": body.language_code,
        "status": "queued",
        "meta_message_id": None,
        "idempotency_key": body.idempotency_key,
        "created_at": now.isoformat(),
        "sent_at": None,
        "delivered_at": None,
        "read_at": None,
        "failed_at": None,
        "error": None,
    }
    await db.messages.insert_one(record)

    # Lookup decrypted business token
    cred = await db.waba_credentials.find_one({"waba_id": phone["waba_id"]})
    if not cred:
        await db.messages.update_one(
            {"_id": msg_id},
            {"$set": {"status": "failed", "failed_at": now.isoformat(), "error": "No credentials"}},
        )
        record["status"] = "failed"
        record["error"] = "No credentials"
        return _serialize_message(record)

    business_token = decrypt(cred["encrypted_business_token"])

    try:
        result = await meta_client.send_template(
            phone_number_id=body.phone_number_id,
            business_token=business_token,
            to_wa_id=body.to_wa_id,
            template_name=body.template_name,
            language_code=body.language_code,
            components=[c.model_dump() for c in body.components] if body.components else None,
        )
        meta_id = result["messages"][0]["id"]
        await db.messages.update_one(
            {"_id": msg_id},
            {
                "$set": {
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "meta_message_id": meta_id,
                }
            },
        )
        record["status"] = "sent"
        record["sent_at"] = datetime.now(timezone.utc).isoformat()
        record["meta_message_id"] = meta_id
    except Exception as e:
        logger.exception("Send failed")
        await db.messages.update_one(
            {"_id": msg_id},
            {
                "$set": {
                    "status": "failed",
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "error": str(e)[:500],
                }
            },
        )
        record["status"] = "failed"
        record["failed_at"] = datetime.now(timezone.utc).isoformat()
        record["error"] = str(e)[:500]

    # Audit
    await db.audit_log.insert_one(
        {
            "_id": str(uuid.uuid4()),
            "tenant_id": p.tenant_id,
            "actor_user_id": p.user_id,
            "action": "message.send",
            "target": msg_id,
            "metadata": {
                "template": body.template_name,
                "to": body.to_wa_id,
                "phone_number_id": body.phone_number_id,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return _serialize_message(record)


@router.get("", response_model=list[MessagePublic])
async def list_messages(
    p: Principal = Depends(require_tenant),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
):
    db = get_db()
    filt: dict = {"tenant_id": p.tenant_id}
    if status_filter:
        filt["status"] = status_filter
    cursor = db.messages.find(filt).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_serialize_message(d) for d in docs]


@router.post("/{message_id}/simulate-webhook")
async def simulate_webhook_for_message(
    message_id: str,
    body: SimulateWebhookRequest,
    p: Principal = Depends(require_tenant),
):
    """Demo helper: generate a properly-signed simulated webhook event for an existing message.

    This calls the public webhook endpoint internally to exercise the full path:
    sign payload -> verify -> enqueue -> worker projects status update.
    """
    db = get_db()
    msg = await db.messages.find_one({"_id": message_id, "tenant_id": p.tenant_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if not msg.get("meta_message_id"):
        raise HTTPException(status_code=400, detail="Message has no meta_message_id yet")

    payload = build_status_webhook_payload(
        phone_number_id=msg["phone_number_id"],
        meta_message_id=msg["meta_message_id"],
        recipient_wa_id=msg.get("to_wa_id", ""),
        status=body.event,
    )
    import json as _json
    raw = _json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = sign_payload(raw)
    # Insert raw event + enqueue (same as webhook endpoint would)
    event_id = str(uuid.uuid4())
    await db.webhook_events_raw.insert_one(
        {
            "_id": event_id,
            "payload": payload,
            "signature_ok": True,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "processed_at": None,
            "status": "received",
            "simulated": True,
        }
    )
    await enqueue("process_webhook", {"event_id": event_id})
    return {"queued": True, "event_id": event_id, "signature": sig}


def build_status_webhook_payload(
    phone_number_id: str,
    meta_message_id: str,
    recipient_wa_id: str,
    status: str,
    pricing_category: str = "utility",
) -> dict:
    """Produce a webhook payload matching the Meta status event shape."""
    ts = int(datetime.now(timezone.utc).timestamp())
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ENTRY_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "",
                                "phone_number_id": phone_number_id,
                            },
                            "statuses": [
                                {
                                    "id": meta_message_id,
                                    "status": status,
                                    "timestamp": str(ts),
                                    "recipient_id": recipient_wa_id,
                                    "pricing": {
                                        "billable": True,
                                        "pricing_model": "CBP",
                                        "category": pricing_category,
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _serialize_message(d: dict) -> dict:
    # Convert ISO strings back to datetimes for the response model
    out = dict(d)
    for k in ("created_at", "sent_at", "delivered_at", "read_at", "failed_at"):
        v = out.get(k)
        if isinstance(v, str):
            try:
                out[k] = datetime.fromisoformat(v)
            except Exception:
                out[k] = None
    return MessagePublic(**out).model_dump(mode="json")
