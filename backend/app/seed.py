"""Seed routine: creates platform super-admin + demo tenant + demo WABA/phone on startup if missing."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from loguru import logger

from .auth import hash_password
from .crypto_utils import encrypt
from .db import get_db
from .models import Role


SUPER_ADMIN_EMAIL = "super@admin.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"
DEMO_OWNER_EMAIL = "owner@demo.com"
DEMO_OWNER_PASSWORD = "Owner123!"
DEMO_TENANT_NAME = "Demo Inc"

# Demo WABA / phone (mock) so simulate-inbound works without live Meta
DEMO_WABA_ID = "demo_waba_seed_001"
DEMO_PHONE_ID = "demo_phone_seed_001"
DEMO_MOCK_TOKEN = "DEMO_MOCK_TOKEN_NOT_REAL"


async def seed_initial_data() -> None:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # ── Super admin ───────────────────────────────────────────────────────────
    if not await db.users.find_one({"email": SUPER_ADMIN_EMAIL}):
        uid = str(uuid.uuid4())
        await db.users.insert_one(
            {
                "_id": uid,
                "id": uid,
                "email": SUPER_ADMIN_EMAIL,
                "password_hash": hash_password(SUPER_ADMIN_PASSWORD),
                "full_name": "Platform Super Admin",
                "role": Role.PlatformSuperAdmin.value,
                "tenant_id": None,
                "mfa_enabled": False,
                "mfa_required": True,
                "mfa_secret_encrypted": None,
                "created_at": now,
            }
        )
        logger.info(f"Seeded super admin: {SUPER_ADMIN_EMAIL}")

    # ── Demo tenant + owner ───────────────────────────────────────────────────
    if not await db.users.find_one({"email": DEMO_OWNER_EMAIL}):
        tid = str(uuid.uuid4())
        await db.tenants.insert_one(
            {"_id": tid, "id": tid, "name": DEMO_TENANT_NAME, "created_at": now}
        )
        uid = str(uuid.uuid4())
        await db.users.insert_one(
            {
                "_id": uid,
                "id": uid,
                "email": DEMO_OWNER_EMAIL,
                "password_hash": hash_password(DEMO_OWNER_PASSWORD),
                "full_name": "Demo Owner",
                "role": Role.TenantOwner.value,
                "tenant_id": tid,
                "mfa_enabled": False,
                "mfa_required": False,
                "mfa_secret_encrypted": None,
                "created_at": now,
            }
        )
        logger.info(f"Seeded demo tenant ({DEMO_TENANT_NAME}) + owner: {DEMO_OWNER_EMAIL}")
    else:
        # Reset demo account on every startup (clean state for demos/tests)
        await db.users.update_one(
            {"email": DEMO_OWNER_EMAIL},
            {
                "$set": {
                    "password_hash": hash_password(DEMO_OWNER_PASSWORD),
                    "mfa_enabled": False,
                    "mfa_required": False,
                },
                "$unset": {"mfa_secret_encrypted": "", "mfa_secret_pending_encrypted": ""},
            },
        )
        logger.info(f"Reset demo account state: {DEMO_OWNER_EMAIL}")

    # ── Seed demo WABA + phone so simulate-inbound works without live Meta ────
    demo_tenant = await db.tenants.find_one({"name": DEMO_TENANT_NAME})
    if not demo_tenant:
        return
    demo_tenant_id = demo_tenant["_id"]

    if not await db.wabas.find_one({"waba_id": DEMO_WABA_ID}):
        waba_internal = str(uuid.uuid4())
        await db.wabas.insert_one({
            "_id": waba_internal,
            "id": waba_internal,
            "tenant_id": demo_tenant_id,
            "waba_id": DEMO_WABA_ID,
            "business_id": "demo_business_seed_001",
            "name": "Demo Business Account (Seed)",
            "is_demo": True,
            "created_at": now,
        })
        await db.waba_credentials.update_one(
            {"waba_id": DEMO_WABA_ID},
            {
                "$setOnInsert": {
                    "_id": f"cred_{DEMO_WABA_ID}",
                    "waba_id": DEMO_WABA_ID,
                    "encrypted_business_token": encrypt(DEMO_MOCK_TOKEN),
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        logger.info(f"Seeded demo WABA: {DEMO_WABA_ID}")

    if not await db.phone_numbers.find_one({"phone_number_id": DEMO_PHONE_ID}):
        pid = str(uuid.uuid4())
        await db.phone_numbers.insert_one({
            "_id": pid,
            "id": pid,
            "tenant_id": demo_tenant_id,
            "waba_id": DEMO_WABA_ID,
            "phone_number_id": DEMO_PHONE_ID,
            "display_phone_number": "+1 (555) 000-0001",
            "verified_name": "Demo Business (Seed)",
            "quality_rating": "GREEN",
            "created_at": now,
        })
        logger.info(f"Seeded demo phone: {DEMO_PHONE_ID}")
