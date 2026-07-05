"""Platform super-admin routes: cross-tenant usage aggregations.

ALL reads here bypass default tenant isolation — this is intentional and
ALWAYS creates an audit-log entry so every elevated access is traceable.
Access is guarded by require_roles(PlatformSuperAdmin).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from .db import get_db
from .models import Role
from .tenancy import Principal, require_roles

router = APIRouter(prefix="/api/platform", tags=["platform"])

_require_sa = require_roles(Role.PlatformSuperAdmin)


# ─── Elevated query pattern ───────────────────────────────────────────────────

async def _audited(action: str, actor_id: str, detail: dict | None = None) -> None:
    """Insert an immutable audit trail for every elevated cross-tenant access."""
    await get_db().audit_log.insert_one({
        "_id": str(uuid.uuid4()),
        "tenant_id": None,
        "actor_user_id": actor_id,
        "action": f"platform.elevated.{action}",
        "metadata": detail or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/overview")
async def platform_overview(
    p: Principal = Depends(_require_sa),
    days: int = Query(default=30, ge=1, le=365),
):
    """Cross-tenant aggregate stats for the platform super-admin dashboard."""
    await _audited("overview", p.user_id, {"days": days})
    db = get_db()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    since_day = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

    total_tenants = await db.tenants.count_documents({})
    total_messages = await db.messages.count_documents({"created_at": {"$gte": since}})
    total_conversations = await db.conversations.count_documents({})

    # Cost rollup (cross-tenant)
    cost_pipeline = [
        {"$match": {"day": {"$gte": since_day}}},
        {"$group": {
            "_id": None,
            "total_cost": {"$sum": "$cost_amount"},
            "total_delivered": {"$sum": "$delivered_count"},
            "total_billable": {"$sum": "$billable_count"},
        }},
    ]
    cost_agg = [d async for d in db.usage_daily_rollup.aggregate(cost_pipeline)]
    cost_data = cost_agg[0] if cost_agg else {"total_cost": 0, "total_delivered": 0, "total_billable": 0}

    # Top tenants by message volume
    top_pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$tenant_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_tenants_raw = [d async for d in db.messages.aggregate(top_pipeline)]
    tenant_ids = [d["_id"] for d in top_tenants_raw if d["_id"]]
    tenant_docs = {d["_id"]: d async for d in db.tenants.find({"_id": {"$in": tenant_ids}})}
    top_tenants = [
        {
            "tenant_id": d["_id"],
            "tenant_name": tenant_docs.get(d["_id"], {}).get("name", d["_id"]),
            "message_count": d["count"],
        }
        for d in top_tenants_raw if d["_id"]
    ]

    return {
        "window_days": days,
        "total_tenants": total_tenants,
        "total_messages": total_messages,
        "total_conversations": total_conversations,
        "total_cost_usd": round(cost_data.get("total_cost", 0), 4),
        "total_delivered": cost_data.get("total_delivered", 0),
        "total_billable": cost_data.get("total_billable", 0),
        "top_tenants_by_volume": top_tenants,
    }


@router.get("/tenants")
async def platform_list_tenants(
    p: Principal = Depends(_require_sa),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, le=200),
):
    """List all tenants with their usage summary."""
    await _audited("list_tenants", p.user_id, {"days": days})
    db = get_db()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    since_day = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

    tenants = await db.tenants.find({}).sort("created_at", -1).limit(limit).to_list(limit)

    # Build usage map from rollup
    rollup_pipeline = [
        {"$match": {"day": {"$gte": since_day}}},
        {"$group": {
            "_id": "$tenant_id",
            "cost": {"$sum": "$cost_amount"},
            "delivered": {"$sum": "$delivered_count"},
            "billable": {"$sum": "$billable_count"},
        }},
    ]
    usage_map = {
        d["_id"]: d async for d in db.usage_daily_rollup.aggregate(rollup_pipeline)
    }

    # Message counts per tenant
    msg_pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$tenant_id", "count": {"$sum": 1}}},
    ]
    msg_map = {d["_id"]: d["count"] async for d in db.messages.aggregate(msg_pipeline)}

    return [
        {
            "tenant_id": t["_id"],
            "tenant_name": t.get("name"),
            "created_at": t.get("created_at"),
            "messages": msg_map.get(t["_id"], 0),
            "delivered": usage_map.get(t["_id"], {}).get("delivered", 0),
            "billable": usage_map.get(t["_id"], {}).get("billable", 0),
            "cost_usd": round(usage_map.get(t["_id"], {}).get("cost", 0), 4),
        }
        for t in tenants
    ]


@router.get("/tenants/{target_tenant_id}/usage")
async def platform_tenant_usage(
    target_tenant_id: str,
    p: Principal = Depends(_require_sa),
    days: int = Query(default=30, ge=1, le=365),
):
    """Per-tenant usage drill-down (elevated, audited)."""
    await _audited("tenant_usage", p.user_id, {"target_tenant": target_tenant_id, "days": days})
    db = get_db()
    tenant = await db.tenants.find_one({"_id": target_tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    since_day = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

    # Message stats
    base = {"tenant_id": target_tenant_id, "created_at": {"$gte": since}}
    total = await db.messages.count_documents(base)
    outbound = await db.messages.count_documents({**base, "direction": "outbound"})
    inbound = await db.messages.count_documents({**base, "direction": "inbound"})

    # Status breakdown
    status_pipeline = [
        {"$match": base},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_bd = {d["_id"] or "unknown": d["count"] async for d in db.messages.aggregate(status_pipeline)}

    # Usage rollup
    rollup = await db.usage_daily_rollup.find(
        {"tenant_id": target_tenant_id, "day": {"$gte": since_day}}
    ).sort("day", 1).to_list(1000)

    total_cost = sum(r.get("cost_amount", 0) for r in rollup)

    return {
        "tenant_id": target_tenant_id,
        "tenant_name": tenant.get("name"),
        "window_days": days,
        "total_messages": total,
        "outbound": outbound,
        "inbound": inbound,
        "status_breakdown": status_bd,
        "total_cost_usd": round(total_cost, 4),
        "daily_rollup": [
            {
                "day": r["day"],
                "category": r.get("category"),
                "delivered_count": r.get("delivered_count", 0),
                "billable_count": r.get("billable_count", 0),
                "free_count": r.get("free_count", 0),
                "cost_amount": round(r.get("cost_amount", 0), 4),
            }
            for r in rollup
        ],
    }


@router.get("/tenants/{target_tenant_id}/export")
async def platform_tenant_export(
    target_tenant_id: str,
    p: Principal = Depends(_require_sa),
    format: str = Query("csv"),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
):
    """Export a specific tenant's usage data (cross-tenant, audited)."""
    await _audited("tenant_export", p.user_id, {
        "target_tenant": target_tenant_id, "format": format,
        "from_date": from_date, "to_date": to_date,
    })
    db = get_db()
    tenant = await db.tenants.find_one({"_id": target_tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from .analytics import _build_export_response
    return await _build_export_response(db, target_tenant_id, format, from_date, to_date)
