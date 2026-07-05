"""MongoDB-backed durable job queue (replaces Redis in this FARM port).

Design:
- `mq_jobs` collection holds {type, payload, status, attempts, claimed_at, created_at}.
- `enqueue` simply inserts a `queued` doc.
- `claim_one` atomically transitions exactly one `queued` job to `processing`
  via `find_one_and_update`, which is single-document atomic in MongoDB.
- Workers ack with `complete` or `fail`; failed jobs are retried up to N times.
- Stale `processing` jobs (older than visibility timeout) are reclaimable.

This is intentionally minimal but durable.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from .db import get_db

VISIBILITY_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 5


async def enqueue(job_type: str, payload: dict[str, Any]) -> str:
    job_id = str(uuid.uuid4())
    await get_db().mq_jobs.insert_one(
        {
            "_id": job_id,
            "type": job_type,
            "payload": payload,
            "status": "queued",
            "attempts": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "claimed_at": None,
            "last_error": None,
        }
    )
    return job_id


async def claim_one() -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    stale_cutoff = (now - timedelta(seconds=VISIBILITY_TIMEOUT_SECONDS)).isoformat()
    doc = await get_db().mq_jobs.find_one_and_update(
        {
            "$or": [
                {"status": "queued"},
                {"status": "processing", "claimed_at": {"$lt": stale_cutoff}},
            ],
            "attempts": {"$lt": MAX_ATTEMPTS},
        },
        {
            "$set": {"status": "processing", "claimed_at": now.isoformat()},
            "$inc": {"attempts": 1},
        },
        sort=[("created_at", 1)],
        return_document=True,
    )
    return doc


async def complete(job_id: str) -> None:
    await get_db().mq_jobs.update_one(
        {"_id": job_id},
        {"$set": {"status": "done", "completed_at": datetime.now(timezone.utc).isoformat()}},
    )


async def fail(job_id: str, error: str) -> None:
    await get_db().mq_jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": "failed",
                "last_error": error[:2000],
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


async def queue_depth() -> dict[str, int]:
    db = get_db()
    out = {}
    for status in ("queued", "processing", "done", "failed"):
        out[status] = await db.mq_jobs.count_documents({"status": status})
    return out
