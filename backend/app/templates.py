"""Template management: full CRUD + Meta Graph submit + two-way sync.

Live mode: create/delete calls the Meta Graph API; status starts PENDING and
transitions via webhook (message_template_status_update) or periodic sync.

Mock mode: auto-approves all templates locally.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from .crypto_utils import decrypt
from .db import get_db
from .meta_client import meta_client
from .models import TemplateComponentSpec, TemplateCreateFull, TemplateStatus
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api/templates", tags=["templates"])

# ─── Pydantic response models ────────────────────────────────────────────────

class TemplatePublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tenant_id: str
    waba_id: str
    name: str
    language: str
    category: str | None = None
    status: str = "PENDING"
    body: str | None = None
    components: list[dict] | None = None
    rejection_reason: str | None = None
    meta_template_id: str | None = None
    source: str | None = None
    created_at: str
    updated_at: str | None = None


class TemplateSyncRequest(BaseModel):
    waba_id: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _extract_body(components: list[dict]) -> str | None:
    for c in components or []:
        if c.get("type") == "BODY":
            return c.get("text")
    return None


def _build_meta_components(components: list[TemplateComponentSpec]) -> list[dict]:
    """Convert our TemplateComponentSpec list → Meta Graph API components format."""
    out = []
    for c in components:
        comp: dict[str, Any] = {"type": c.type}
        if c.type == "HEADER":
            comp["format"] = (c.format or "TEXT")
            if comp["format"] == "TEXT":
                comp["text"] = c.text or ""
                if c.example_header_text:
                    comp["example"] = {"header_text": c.example_header_text}
        elif c.type == "BODY":
            comp["text"] = c.text or ""
            if c.example_body_text:
                comp["example"] = {"body_text": c.example_body_text}
        elif c.type == "FOOTER":
            comp["text"] = c.text or ""
        elif c.type == "BUTTONS":
            btns = []
            for btn in (c.buttons or []):
                b: dict[str, Any] = {"type": btn.type, "text": btn.text}
                if btn.type == "URL":
                    b["url"] = btn.url or ""
                    if btn.url_example:
                        b["example"] = [btn.url_example]
                elif btn.type == "PHONE_NUMBER":
                    b["phone_number"] = btn.phone_number or ""
                btns.append(b)
            comp["buttons"] = btns
        out.append(comp)
    return out


def _serialize(d: dict) -> dict:
    return TemplatePublic(**d).model_dump(mode="json")


async def _get_token(db, waba_id: str) -> str:
    cred = await db.waba_credentials.find_one({"waba_id": waba_id})
    if not cred:
        return ""
    return decrypt(cred["encrypted_business_token"])


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TemplatePublic])
async def list_templates(
    p: Principal = Depends(require_tenant),
    waba_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
    search: str | None = Query(default=None),
):
    filt: dict = {"tenant_id": p.tenant_id}
    if waba_id:
        filt["waba_id"] = waba_id
    if status:
        filt["status"] = status.upper()
    if category:
        filt["category"] = category.upper()
    if language:
        filt["language"] = language
    if search:
        filt["name"] = {"$regex": re.escape(search), "$options": "i"}
    docs = await get_db().templates.find(filt).sort("updated_at", -1).to_list(500)
    return [_serialize(d) for d in docs]


@router.get("/{template_id}", response_model=TemplatePublic)
async def get_template(template_id: str, p: Principal = Depends(require_tenant)):
    doc = await get_db().templates.find_one(
        {"_id": template_id, "tenant_id": p.tenant_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return _serialize(doc)


@router.post("", response_model=TemplatePublic)
async def create_template(body: TemplateCreateFull, p: Principal = Depends(require_tenant)):
    db = get_db()
    waba = await db.wabas.find_one({"waba_id": body.waba_id, "tenant_id": p.tenant_id})
    if not waba:
        raise HTTPException(status_code=404, detail="WABA not found")

    existing = await db.templates.find_one({
        "tenant_id": p.tenant_id,
        "waba_id": body.waba_id,
        "name": body.name,
        "language": body.language,
    })
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Template with that name + language already exists for this WABA",
        )

    meta_components = _build_meta_components(body.components)
    token = await _get_token(db, body.waba_id)

    meta_resp = await meta_client.create_template(
        waba_id=body.waba_id,
        business_token=token,
        name=body.name,
        language=body.language,
        category=body.category,
        components=meta_components,
    )

    now = datetime.now(timezone.utc).isoformat()
    status_val = meta_resp.get("status", "PENDING") if not meta_client.mock else "APPROVED"
    meta_id = str(meta_resp.get("id") or "")

    # Store components as plain dicts
    comp_dicts = [c.model_dump(exclude_none=True) for c in body.components]

    tid = str(uuid.uuid4())
    doc = {
        "_id": tid,
        "id": tid,
        "tenant_id": p.tenant_id,
        "waba_id": body.waba_id,
        "name": body.name,
        "language": body.language,
        "category": body.category,
        "body": _extract_body(meta_components),
        "components": comp_dicts,
        "status": status_val,
        "meta_template_id": meta_id,
        "rejection_reason": None,
        "source": "local",
        "created_at": now,
        "updated_at": now,
    }
    await db.templates.insert_one(doc)
    logger.info(f"Template {body.name}/{body.language} created (status={status_val})")
    return _serialize(doc)


@router.delete("/{template_id}")
async def delete_template(template_id: str, p: Principal = Depends(require_tenant)):
    db = get_db()
    tmpl = await db.templates.find_one({"_id": template_id, "tenant_id": p.tenant_id})
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    token = await _get_token(db, tmpl["waba_id"])
    try:
        await meta_client.delete_template(
            waba_id=tmpl["waba_id"],
            business_token=token,
            name=tmpl["name"],
            meta_template_id=tmpl.get("meta_template_id"),
        )
    except Exception as exc:
        logger.warning(f"Meta delete template failed (still removing from DB): {exc}")

    await db.templates.delete_one({"_id": template_id, "tenant_id": p.tenant_id})
    return {"deleted": True}


@router.post("/sync")
async def sync_templates(body: TemplateSyncRequest, p: Principal = Depends(require_tenant)):
    db = get_db()
    waba = await db.wabas.find_one({"waba_id": body.waba_id, "tenant_id": p.tenant_id})
    if not waba:
        raise HTTPException(status_code=404, detail="WABA not found")

    token = await _get_token(db, body.waba_id)
    fetched = await meta_client.list_templates(body.waba_id, token)
    now = datetime.now(timezone.utc).isoformat()
    upserts = 0
    for t in fetched:
        key = {
            "tenant_id": p.tenant_id,
            "waba_id": body.waba_id,
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
        upserts += 1
    # Update WABA last_synced_at
    await db.wabas.update_one(
        {"waba_id": body.waba_id}, {"$set": {"templates_last_synced_at": now}}
    )
    logger.info(f"Synced {upserts} templates tenant={p.tenant_id} waba={body.waba_id}")
    return {"synced": upserts}


async def apply_template_status_update(
    waba_id: str,
    template_name: str,
    language: str,
    new_status: str,
    reason: str | None,
) -> None:
    """Called by the worker when a message_template_status_update webhook arrives."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    result = await db.templates.update_many(
        {"waba_id": waba_id, "name": template_name, "language": language},
        {
            "$set": {
                "status": new_status,
                "rejection_reason": reason,
                "updated_at": now,
            }
        },
    )
    logger.info(
        f"Template status updated: {template_name}/{language} -> {new_status} "
        f"(modified={result.modified_count})"
    )
