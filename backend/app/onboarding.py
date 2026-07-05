"""Onboarding flow: exchange Embedded Signup code for business token, persist."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from .crypto_utils import encrypt
from .db import get_db
from .meta_client import meta_client
from .models import EmbeddedSignupExchange, WabaPublic, PhoneNumberPublic
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post("/exchange")
async def exchange(
    body: EmbeddedSignupExchange,
    p: Principal = Depends(require_tenant),
):
    """Server-side exchange of the auth code for a long-lived business token.

    In LIVE mode: the front-end Facebook JS SDK returns `code`, `waba_id`,
    `phone_number_id` (and optionally `business_id`) in the FB.login callback.
    All four should be posted to this endpoint. We exchange the code for a
    business access token via /oauth/access_token, then subscribe the app to
    the WABA's webhooks and register the phone number.

    In MOCK mode the meta_client synthesises a WABA/phone if none supplied.
    Business tokens are encrypted at rest with Fernet before storage and are
    NEVER returned in the response.
    """
    from .config import settings as _settings

    db = get_db()
    res = await meta_client.exchange_code_for_business_token(body.code)

    # In live mode the token-exchange response does NOT include waba_id /
    # phone_number_id — they come from the front-end Embedded Signup callback.
    # In mock mode meta_client synthesises them.
    waba_id = body.waba_id or res.get("waba_id")
    phone_number_id = body.phone_number_id or res.get("phone_number_id")
    business_token = res["access_token"]

    if not waba_id or not phone_number_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "waba_id and phone_number_id are required (returned by the "
                "Embedded Signup dialog alongside the auth code)."
            ),
        )

    # Subscribe app to WABA + register phone (real HTTP calls in live mode)
    await meta_client.subscribe_app_to_waba(waba_id, business_token)
    await meta_client.register_phone_number(phone_number_id, business_token)

    # Enrich WABA + phone metadata from Meta in live mode
    waba_info = await meta_client.get_waba_info(waba_id, business_token)
    phone_info = await meta_client.get_phone_info(phone_number_id, business_token)

    # Fall back to Embedded Signup callback fields, then res, then defaults
    waba_name = (
        waba_info.get("name")
        or res.get("verified_name")
        or "Business Account"
    )
    business_id = (
        body.business_id or waba_info.get("business_id") or res.get("business_id")
    )
    display_phone_number = (
        phone_info.get("display_phone_number") or res.get("display_phone_number")
    )
    verified_name = phone_info.get("verified_name") or res.get("verified_name")
    quality_rating = (
        phone_info.get("quality_rating") or res.get("quality_rating") or "GREEN"
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    # Persist WABA (idempotent on waba_id)
    waba_internal_id = str(uuid.uuid4())
    await db.wabas.update_one(
        {"waba_id": waba_id},
        {
            "$setOnInsert": {
                "_id": waba_internal_id,
                "id": waba_internal_id,
                "tenant_id": p.tenant_id,
                "waba_id": waba_id,
                "business_id": business_id,
                "name": waba_name,
                "created_at": now_iso,
            }
        },
        upsert=True,
    )
    waba_doc = await db.wabas.find_one({"waba_id": waba_id})
    # Enforce isolation: a WABA already belonging to another tenant cannot be claimed
    if waba_doc["tenant_id"] != p.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="WABA already claimed by another tenant",
        )

    # Encrypted credentials
    await db.waba_credentials.update_one(
        {"waba_id": waba_id},
        {
            "$set": {
                "waba_id": waba_id,
                "encrypted_business_token": encrypt(business_token),
                "updated_at": now_iso,
            },
            "$setOnInsert": {"_id": f"cred_{waba_id}", "created_at": now_iso},
        },
        upsert=True,
    )

    # Persist phone
    phone_internal_id = str(uuid.uuid4())
    await db.phone_numbers.update_one(
        {"phone_number_id": phone_number_id},
        {
            "$setOnInsert": {
                "_id": phone_internal_id,
                "id": phone_internal_id,
                "tenant_id": p.tenant_id,
                "waba_id": waba_id,
                "phone_number_id": phone_number_id,
                "display_phone_number": display_phone_number,
                "verified_name": verified_name,
                "quality_rating": quality_rating,
                "created_at": now_iso,
            }
        },
        upsert=True,
    )

    logger.info(f"Tenant {p.tenant_id} onboarded WABA {waba_id} phone {phone_number_id}")

    waba_out = await db.wabas.find_one({"waba_id": waba_id})
    phone_out = await db.phone_numbers.find_one({"phone_number_id": phone_number_id})
    return {
        "waba": _serialize_waba(waba_out),
        "phone_number": _serialize_phone(phone_out),
    }


def _serialize_waba(doc: dict) -> dict:
    return WabaPublic(**doc).model_dump(mode="json")


def _serialize_phone(doc: dict) -> dict:
    return PhoneNumberPublic(**doc).model_dump(mode="json")
