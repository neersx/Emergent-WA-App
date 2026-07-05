"""Template management: CRUD + sync (mock or live Meta).

A "template" is an approved WhatsApp message template tied to a WABA.
Mock mode synthesizes a stable set of demo templates per WABA on sync; live mode
calls the Meta Graph endpoint `{waba_id}/message_templates`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from .crypto_utils import decrypt
from .db import get_db
from .meta_client import meta_client
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplatePublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tenant_id: str
    waba_id: str
    name: str
    language: str
    category: str | None = None
    status: str = "APPROVED"
    body: str | None = None
    created_at: str
    updated_at: str | None = None


class TemplateCreate(BaseModel):
    waba_id: str
    name: str = Field(min_length=1, max_length=120)
    language: str = Field(default="en_US", min_length=2, max_length=16)
    category: Literal["UTILITY", "MARKETING", "AUTHENTICATION"] = "UTILITY"
    body: str = Field(min_length=1, max_length=1024)


class TemplateSyncRequest(BaseModel):
    waba_id: str


def _serialize(d: dict) -> dict:
    return TemplatePublic(**d).model_dump(mode="json")


@router.get("", response_model=list[TemplatePublic])
async def list_templates(
    p: Principal = Depends(require_tenant),
    waba_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    filt: dict = {"tenant_id": p.tenant_id}
    if waba_id:
        filt["waba_id"] = waba_id
    if status:
        filt["status"] = status
    docs = (
        await get_db().templates.find(filt).sort("updated_at", -1).to_list(500)
    )
    return [_serialize(d) for d in docs]


@router.post("", response_model=TemplatePublic)
async def create_template(
    body: TemplateCreate, p: Principal = Depends(require_tenant)
):
    db = get_db()
    waba = await db.wabas.find_one({"waba_id": body.waba_id, "tenant_id": p.tenant_id})
    if not waba:
        raise HTTPException(status_code=404, detail="WABA not found")
    # Idempotent on (tenant, waba, name, language)
    existing = await db.templates.find_one(
        {
            "tenant_id": p.tenant_id,
            "waba_id": body.waba_id,
            "name": body.name,
            "language": body.language,
        }
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Template with that name + language already exists for this WABA",
        )
    now = datetime.now(timezone.utc).isoformat()
    tid = str(uuid.uuid4())
    doc = {
        "_id": tid,
        "id": tid,
        "tenant_id": p.tenant_id,
        "waba_id": body.waba_id,
        "name": body.name,
        "language": body.language,
        "category": body.category,
        "body": body.body,
        "status": "APPROVED",  # In mock mode we auto-approve.
        "created_at": now,
        "updated_at": now,
        "source": "local",
    }
    await db.templates.insert_one(doc)
    return _serialize(doc)


@router.post("/sync")
async def sync_templates(
    body: TemplateSyncRequest, p: Principal = Depends(require_tenant)
):
    db = get_db()
    waba = await db.wabas.find_one({"waba_id": body.waba_id, "tenant_id": p.tenant_id})
    if not waba:
        raise HTTPException(status_code=404, detail="WABA not found")

    cred = await db.waba_credentials.find_one({"waba_id": body.waba_id})
    business_token = decrypt(cred["encrypted_business_token"]) if cred else ""

    fetched = await meta_client.list_templates(body.waba_id, business_token)
    now = datetime.now(timezone.utc).isoformat()
    upserts = 0
    for t in fetched:
        tid_key = {
            "tenant_id": p.tenant_id,
            "waba_id": body.waba_id,
            "name": t["name"],
            "language": t.get("language", "en_US"),
        }
        await db.templates.update_one(
            tid_key,
            {
                "$set": {
                    "tenant_id": p.tenant_id,
                    "waba_id": body.waba_id,
                    "name": t["name"],
                    "language": t.get("language", "en_US"),
                    "category": t.get("category"),
                    "body": t.get("body"),
                    "status": t.get("status", "APPROVED"),
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
        upserts += 1
    logger.info(
        f"Synced {upserts} templates for tenant={p.tenant_id} waba={body.waba_id}"
    )
    return {"synced": upserts}


@router.delete("/{template_id}")
async def delete_template(
    template_id: str, p: Principal = Depends(require_tenant)
):
    res = await get_db().templates.delete_one(
        {"_id": template_id, "tenant_id": p.tenant_id}
    )
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True}
