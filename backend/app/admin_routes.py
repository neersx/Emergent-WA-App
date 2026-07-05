"""Admin (tenant-scoped) routes for WABAs, phone numbers, dashboard summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .db import get_db
from .models import PhoneNumberPublic, WabaPublic
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/wabas", response_model=list[WabaPublic])
async def list_wabas(p: Principal = Depends(require_tenant)):
    docs = await get_db().wabas.find({"tenant_id": p.tenant_id}).sort("created_at", -1).to_list(200)
    return [WabaPublic(**d).model_dump(mode="json") for d in docs]


@router.get("/phone-numbers", response_model=list[PhoneNumberPublic])
async def list_phone_numbers(p: Principal = Depends(require_tenant)):
    docs = await get_db().phone_numbers.find({"tenant_id": p.tenant_id}).sort("created_at", -1).to_list(200)
    return [PhoneNumberPublic(**d).model_dump(mode="json") for d in docs]


@router.get("/dashboard")
async def dashboard(p: Principal = Depends(require_tenant)):
    db = get_db()
    waba_count = await db.wabas.count_documents({"tenant_id": p.tenant_id})
    phone_count = await db.phone_numbers.count_documents({"tenant_id": p.tenant_id})
    msg_count = await db.messages.count_documents({"tenant_id": p.tenant_id})
    sent_count = await db.messages.count_documents({"tenant_id": p.tenant_id, "status": "sent"})
    delivered_count = await db.messages.count_documents(
        {"tenant_id": p.tenant_id, "status": "delivered"}
    )
    read_count = await db.messages.count_documents({"tenant_id": p.tenant_id, "status": "read"})
    return {
        "waba_count": waba_count,
        "phone_count": phone_count,
        "message_count": msg_count,
        "sent_count": sent_count,
        "delivered_count": delivered_count,
        "read_count": read_count,
    }


@router.get("/audit")
async def audit_log(p: Principal = Depends(require_tenant), limit: int = 100):
    docs = (
        await get_db()
        .audit_log.find({"tenant_id": p.tenant_id})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    for d in docs:
        d["id"] = d.pop("_id")
    return docs
