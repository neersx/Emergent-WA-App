"""Background worker: claims jobs from mq_jobs and projects events.

Runs as an asyncio task inside the FastAPI process (Emergent runs one process
under supervisor). The worker loop is fully cooperative and yields between
jobs so request handlers remain responsive.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from .config import settings
from .db import get_db
from .queue import claim_one, complete, fail

_worker_task: asyncio.Task | None = None
_stop = asyncio.Event()


async def _project_webhook(event_id: str) -> None:
    """Project a stored raw webhook event into messages/conversations updates.

    Supports the standard WhatsApp webhook payload shape:
      entry[].changes[].value.statuses[]    -> status updates (sent/delivered/read/failed)
      entry[].changes[].value.messages[]    -> inbound messages
      entry[].changes[].value.pricing/...   -> pricing info on statuses
    """
    db = get_db()
    raw = await db.webhook_events_raw.find_one({"_id": event_id})
    if not raw:
        logger.warning(f"Webhook event {event_id} not found")
        return

    payload = raw.get("payload") or {}
    now_iso = datetime.now(timezone.utc).isoformat()

    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id")

            # Status updates
            for st in value.get("statuses", []) or []:
                meta_message_id = st.get("id")
                status_name = st.get("status")  # sent | delivered | read | failed
                if not meta_message_id or not status_name:
                    continue
                ts_field = {
                    "sent": "sent_at",
                    "delivered": "delivered_at",
                    "read": "read_at",
                    "failed": "failed_at",
                }.get(status_name)
                update: dict[str, Any] = {"status": status_name, "updated_at": now_iso}
                if ts_field:
                    update[ts_field] = now_iso
                # Pricing/conversation fields, if present
                pricing = st.get("pricing") or {}
                if pricing:
                    update["pricing_category"] = pricing.get("category")
                    update["pricing_billable"] = pricing.get("billable")
                if st.get("errors"):
                    update["error"] = (st.get("errors") or [{}])[0].get("title")
                await db.messages.update_one(
                    {"meta_message_id": meta_message_id}, {"$set": update}
                )

            # Inbound messages -> create message + bump conversation
            for msg in value.get("messages", []) or []:
                from_wa_id = msg.get("from")
                meta_message_id = msg.get("id")
                # Determine tenant from phone_number_id mapping
                phone_doc = (
                    await db.phone_numbers.find_one({"phone_number_id": phone_number_id})
                    if phone_number_id
                    else None
                )
                tenant_id = phone_doc["tenant_id"] if phone_doc else None
                if not tenant_id:
                    continue
                # Upsert conversation
                conv = await db.conversations.find_one_and_update(
                    {
                        "tenant_id": tenant_id,
                        "phone_number_id": phone_number_id,
                        "contact_wa_id": from_wa_id,
                    },
                    {
                        "$set": {"last_inbound_at": now_iso, "updated_at": now_iso},
                        "$setOnInsert": {
                            "_id": f"conv_{phone_number_id}_{from_wa_id}",
                            "id": f"conv_{phone_number_id}_{from_wa_id}",
                            "tenant_id": tenant_id,
                            "phone_number_id": phone_number_id,
                            "contact_wa_id": from_wa_id,
                            "created_at": now_iso,
                        },
                    },
                    upsert=True,
                    return_document=True,
                )
                # Persist inbound message
                import uuid as _uuid
                mid = str(_uuid.uuid4())
                await db.messages.insert_one(
                    {
                        "_id": mid,
                        "id": mid,
                        "tenant_id": tenant_id,
                        "phone_number_id": phone_number_id,
                        "conversation_id": conv["id"] if conv else None,
                        "direction": "inbound",
                        "from_wa_id": from_wa_id,
                        "meta_message_id": meta_message_id,
                        "status": "delivered",
                        "body": msg.get("text", {}).get("body") if isinstance(msg.get("text"), dict) else None,
                        "created_at": now_iso,
                    }
                )

    await db.webhook_events_raw.update_one(
        {"_id": event_id}, {"$set": {"processed_at": now_iso, "status": "processed"}}
    )


async def _handle_job(job: dict) -> None:
    job_type = job["type"]
    if job_type == "process_webhook":
        await _project_webhook(job["payload"]["event_id"])
    else:
        raise ValueError(f"Unknown job type: {job_type}")


async def worker_loop() -> None:
    poll_seconds = settings.WORKER_POLL_INTERVAL_MS / 1000
    logger.info(f"Worker started (poll={poll_seconds}s)")
    while not _stop.is_set():
        try:
            job = await claim_one()
            if not job:
                await asyncio.sleep(poll_seconds)
                continue
            try:
                await _handle_job(job)
                await complete(job["_id"])
            except Exception as e:  # pragma: no cover
                logger.exception(f"Job {job['_id']} failed: {e}")
                await fail(job["_id"], str(e))
        except asyncio.CancelledError:
            break
        except Exception as e:  # pragma: no cover
            logger.exception(f"Worker loop error: {e}")
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
