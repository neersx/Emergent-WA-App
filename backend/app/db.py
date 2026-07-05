"""MongoDB client + index setup + seed."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from loguru import logger

from .config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[settings.DB_NAME]
    return _db


async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True, name="uniq_email"),
        IndexModel([("tenant_id", ASCENDING)], name="by_tenant"),
    ])
    await db.refresh_tokens.create_indexes([
        IndexModel([("user_id", ASCENDING)], name="by_user"),
        IndexModel([("token_hash", ASCENDING)], unique=True, name="uniq_token_hash"),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expires"),
    ])
    await db.password_resets.create_indexes([
        IndexModel([("token_hash", ASCENDING)], unique=True, name="uniq_reset_hash"),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_reset"),
    ])
    await db.tenants.create_indexes([
        IndexModel([("name", ASCENDING)], name="by_name"),
    ])
    await db.wabas.create_indexes([
        IndexModel([("tenant_id", ASCENDING)], name="by_tenant"),
        IndexModel([("waba_id", ASCENDING)], unique=True, name="uniq_waba"),
    ])
    await db.waba_credentials.create_indexes([
        IndexModel([("waba_id", ASCENDING)], unique=True, name="uniq_cred"),
    ])
    await db.phone_numbers.create_indexes([
        IndexModel([("tenant_id", ASCENDING)], name="by_tenant"),
        IndexModel([("phone_number_id", ASCENDING)], unique=True, name="uniq_phone"),
    ])
    await db.messages.create_indexes([
        IndexModel([("tenant_id", ASCENDING), ("created_at", DESCENDING)], name="by_tenant_time"),
        IndexModel([("meta_message_id", ASCENDING)], name="by_meta_id", sparse=True),
        IndexModel([("idempotency_key", ASCENDING)], name="by_idem", sparse=True),
    ])
    await db.conversations.create_indexes([
        IndexModel([("tenant_id", ASCENDING)], name="by_tenant"),
        IndexModel([("phone_number_id", ASCENDING), ("contact_wa_id", ASCENDING)], name="by_phone_contact"),
    ])
    await db.webhook_events_raw.create_indexes([
        IndexModel([("received_at", DESCENDING)], name="by_time"),
    ])
    await db.mq_jobs.create_indexes([
        IndexModel([("status", ASCENDING), ("claimed_at", ASCENDING)], name="by_status"),
    ])
    await db.idempotency_keys.create_indexes([
        IndexModel([("tenant_id", ASCENDING), ("key", ASCENDING)], unique=True, name="uniq_idem"),
        IndexModel([("created_at", ASCENDING)], expireAfterSeconds=86400, name="ttl_idem"),
    ])
    await db.audit_log.create_indexes([
        IndexModel([("tenant_id", ASCENDING), ("created_at", DESCENDING)], name="by_tenant_time"),
    ])
    await db.templates.create_indexes([
        IndexModel([("tenant_id", ASCENDING), ("waba_id", ASCENDING)], name="by_tenant_waba"),
        IndexModel(
            [("tenant_id", ASCENDING), ("waba_id", ASCENDING), ("name", ASCENDING), ("language", ASCENDING)],
            unique=True,
            name="uniq_template",
        ),
        IndexModel([("meta_template_id", ASCENDING)], name="by_meta_tpl_id", sparse=True),
    ])
    await db.usage_daily_rollup.create_indexes([
        IndexModel([("tenant_id", ASCENDING), ("day", DESCENDING)], name="by_tenant_day"),
        IndexModel([("day", DESCENDING)], name="by_day_global"),
    ])
    await db.media_assets.create_indexes([
        IndexModel([("tenant_id", ASCENDING), ("meta_media_id", ASCENDING)], unique=True, name="uniq_media"),
        IndexModel([("message_id", ASCENDING)], name="by_message"),
    ])
    await db.template_perf_rollup.create_indexes([
        IndexModel([("tenant_id", ASCENDING), ("month", DESCENDING)], name="by_tenant_month"),
        IndexModel([("tenant_id", ASCENDING), ("template_name", ASCENDING), ("month", DESCENDING)], name="by_tpl_month"),
    ])
    await db.messages.create_indexes([
        IndexModel([("tenant_id", ASCENDING), ("created_at", DESCENDING)], name="by_tenant_time"),
        IndexModel([("tenant_id", ASCENDING), ("month", ASCENDING), ("created_at", DESCENDING)], name="by_tenant_month_time", sparse=True),
        IndexModel([("tenant_id", ASCENDING), ("conversation_id", ASCENDING), ("created_at", ASCENDING)], name="by_conv_time"),
        IndexModel([("meta_message_id", ASCENDING)], name="by_meta_id", sparse=True),
        IndexModel([("idempotency_key", ASCENDING)], name="by_idem", sparse=True),
    ])
    logger.info("MongoDB indexes ensured")


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
