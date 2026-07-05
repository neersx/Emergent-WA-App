"""Analytics endpoints (read-only roll-ups of the messages collection).

All queries are scoped to the principal's tenant.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query

from .db import get_db
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(
    p: Principal = Depends(require_tenant),
    days: int = Query(default=14, ge=1, le=90),
):
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_iso = since.isoformat()

    base = {"tenant_id": p.tenant_id, "created_at": {"$gte": since_iso}}
    total = await db.messages.count_documents(base)
    outbound = await db.messages.count_documents({**base, "direction": "outbound"})
    inbound = await db.messages.count_documents({**base, "direction": "inbound"})

    status_pipeline = [
        {"$match": base},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_breakdown = {
        row["_id"] or "unknown": row["count"]
        async for row in db.messages.aggregate(status_pipeline)
    }

    # Delivery rate of outbound messages
    delivered = (
        status_breakdown.get("delivered", 0) + status_breakdown.get("read", 0)
    )
    failed = status_breakdown.get("failed", 0)
    delivery_rate = (
        delivered / outbound if outbound else 0.0
    )

    # Conversations + service window stats
    conv_total = await db.conversations.count_documents({"tenant_id": p.tenant_id})
    open_window_cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).isoformat()
    conv_open_window = await db.conversations.count_documents(
        {"tenant_id": p.tenant_id, "last_inbound_at": {"$gte": open_window_cutoff}}
    )

    return {
        "window_days": days,
        "total_messages": total,
        "outbound": outbound,
        "inbound": inbound,
        "status_breakdown": status_breakdown,
        "delivered": delivered,
        "failed": failed,
        "delivery_rate": round(delivery_rate, 4),
        "conversations": conv_total,
        "conversations_open_window": conv_open_window,
    }


@router.get("/timeseries")
async def timeseries(
    p: Principal = Depends(require_tenant),
    days: int = Query(default=14, ge=1, le=90),
):
    """Daily counts of outbound + inbound + delivered + failed."""
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_iso = since.isoformat()

    # Build empty buckets so the chart has a continuous x-axis
    buckets: dict[str, dict] = {}
    for i in range(days):
        d = (since + timedelta(days=i)).date().isoformat()
        buckets[d] = {
            "date": d,
            "outbound": 0,
            "inbound": 0,
            "delivered": 0,
            "read": 0,
            "failed": 0,
        }

    pipeline = [
        {
            "$match": {
                "tenant_id": p.tenant_id,
                "created_at": {"$gte": since_iso},
            }
        },
        {
            "$addFields": {
                # created_at is stored as ISO 8601 string. Take YYYY-MM-DD substring.
                "day": {"$substr": ["$created_at", 0, 10]},
            }
        },
        {
            "$group": {
                "_id": {"day": "$day", "direction": "$direction", "status": "$status"},
                "count": {"$sum": 1},
            }
        },
    ]
    async for row in db.messages.aggregate(pipeline):
        day = row["_id"]["day"]
        bucket = buckets.get(day)
        if not bucket:
            buckets[day] = {
                "date": day,
                "outbound": 0,
                "inbound": 0,
                "delivered": 0,
                "read": 0,
                "failed": 0,
            }
            bucket = buckets[day]
        direction = row["_id"].get("direction") or ""
        status = row["_id"].get("status") or ""
        if direction == "outbound":
            bucket["outbound"] += row["count"]
        elif direction == "inbound":
            bucket["inbound"] += row["count"]
        if status in ("delivered", "read", "failed"):
            bucket[status] += row["count"]
    return sorted(buckets.values(), key=lambda b: b["date"])


@router.get("/by-template")
async def by_template(
    p: Principal = Depends(require_tenant),
    days: int = Query(default=14, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=50),
):
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_iso = since.isoformat()
    pipeline = [
        {
            "$match": {
                "tenant_id": p.tenant_id,
                "created_at": {"$gte": since_iso},
                "direction": "outbound",
                "template_name": {"$ne": None},
            }
        },
        {
            "$group": {
                "_id": "$template_name",
                "sent": {"$sum": 1},
                "delivered": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$status", ["delivered", "read"]]},
                            1,
                            0,
                        ]
                    }
                },
                "failed": {
                    "$sum": {
                        "$cond": [{"$eq": ["$status", "failed"]}, 1, 0]
                    }
                },
            }
        },
        {"$sort": {"sent": -1}},
        {"$limit": limit},
    ]
    out = []
    async for r in db.messages.aggregate(pipeline):
        out.append(
            {
                "template_name": r["_id"],
                "sent": r["sent"],
                "delivered": r["delivered"],
                "failed": r["failed"],
                "delivery_rate": round(r["delivered"] / r["sent"], 4)
                if r["sent"]
                else 0.0,
            }
        )
    return out


@router.get("/by-phone")
async def by_phone(
    p: Principal = Depends(require_tenant),
    days: int = Query(default=14, ge=1, le=90),
):
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_iso = since.isoformat()
    # Join via simple lookup since phone_numbers is small
    phones = {
        p2["phone_number_id"]: p2
        async for p2 in db.phone_numbers.find({"tenant_id": p.tenant_id})
    }
    pipeline = [
        {
            "$match": {
                "tenant_id": p.tenant_id,
                "created_at": {"$gte": since_iso},
            }
        },
        {
            "$group": {
                "_id": "$phone_number_id",
                "outbound": {
                    "$sum": {"$cond": [{"$eq": ["$direction", "outbound"]}, 1, 0]}
                },
                "inbound": {
                    "$sum": {"$cond": [{"$eq": ["$direction", "inbound"]}, 1, 0]}
                },
            }
        },
    ]
    out = []
    async for r in db.messages.aggregate(pipeline):
        pid = r["_id"]
        phone = phones.get(pid)
        out.append(
            {
                "phone_number_id": pid,
                "display": phone["display_phone_number"] if phone else pid,
                "verified_name": phone["verified_name"] if phone else None,
                "outbound": r["outbound"],
                "inbound": r["inbound"],
            }
        )
    out.sort(key=lambda x: x["outbound"] + x["inbound"], reverse=True)
    return out
