"""FastAPI application factory and entry point.

Wires together:
- Auth routes (register, login, logout, MFA, password reset, refresh)
- Onboarding (Embedded Signup exchange — mock mode)
- Messaging (send template, list messages, simulate webhook helper)
- Admin (WABAs, phone numbers, dashboard, audit)
- Webhooks (Meta GET/POST)
- Health + Prometheus metrics
- Background worker (asyncio task with MongoDB-backed queue)
- Startup seed (super admin + demo tenant)
"""
from __future__ import annotations

import sys
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.cors import CORSMiddleware

from app.admin_routes import router as admin_router
from app.analytics import router as analytics_router
from app.auth_routes import router as auth_router
from app.config import settings
from app.db import close_db, ensure_indexes, get_db
from app.health import router as health_router
from app.inbox import router as inbox_router
from app.media import router as media_router
from app.messaging import router as messaging_router
from app.onboarding import router as onboarding_router
from app.seed import seed_initial_data
from app.templates import router as templates_router
from app.webhooks import router as webhook_router
from app.worker import start_worker, stop_worker
from app.ws import router as ws_router
from app.platform import router as platform_router


# ----- Logging -----
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[trace_id]}</cyan> | {message}",
    backtrace=False,
    diagnose=False,
)
logger.configure(extra={"trace_id": "-"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    await seed_initial_data()
    start_worker()
    logger.info(
        f"Startup complete (mock_mode={settings.META_MOCK_MODE}, worker_enabled={settings.WORKER_ENABLED})"
    )
    try:
        yield
    finally:
        await stop_worker()
        await close_db()


app = FastAPI(
    title="WhatsApp SaaS Platform",
    description="Multi-tenant WhatsApp Business Platform (FARM-stack port of the .NET/Angular spec).",
    version="1.0.0-mvp",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Trace id middleware -----
@app.middleware("http")
async def trace_id_mw(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:12]
    with logger.contextualize(trace_id=trace_id):
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception(f"Unhandled error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "trace_id": trace_id},
            )
        response.headers["X-Trace-Id"] = trace_id
        return response


# Routers
app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(messaging_router)
app.include_router(templates_router)
app.include_router(inbox_router)
app.include_router(media_router)
app.include_router(analytics_router)
app.include_router(admin_router)
app.include_router(webhook_router)
app.include_router(health_router)
app.include_router(ws_router)
app.include_router(platform_router)


@app.get("/api/")
async def root():
    return {
        "app": "whatsapp-saas",
        "version": "1.0.0-mvp",
        "mock_mode": settings.META_MOCK_MODE,
    }


@app.get("/api/system/info")
async def system_info():
    """Public system info. The app_id + embedded_signup_config_id ARE public
    (they're embedded into the front-end FB JS SDK anyway); the secret and
    verify-token are NEVER returned."""
    return {
        "app": "whatsapp-saas",
        "version": "1.0.0-mvp",
        "mock_mode": settings.META_MOCK_MODE,
        "meta_graph_api_version": settings.META_GRAPH_API_VERSION,
        "meta_app_id": settings.META_APP_ID if not settings.META_MOCK_MODE else "",
        "meta_embedded_signup_config_id": (
            settings.META_EMBEDDED_SIGNUP_CONFIG_ID if not settings.META_MOCK_MODE else ""
        ),
        "meta_app_id_configured": bool(settings.META_APP_ID and settings.META_APP_ID != "000000000000000"),
        "meta_embedded_signup_config_id_configured": bool(
            settings.META_EMBEDDED_SIGNUP_CONFIG_ID
            and settings.META_EMBEDDED_SIGNUP_CONFIG_ID != "000000000000000"
        ),
        "meta_webhook_verify_token_configured": bool(
            settings.META_WEBHOOK_VERIFY_TOKEN
            and settings.META_WEBHOOK_VERIFY_TOKEN != "mock-verify-token"
        ),
        "worker_enabled": settings.WORKER_ENABLED,
        "send_rate_limit_per_min": settings.SEND_RATE_LIMIT_PER_MIN,
        "access_token_ttl_minutes": settings.ACCESS_TOKEN_TTL_MINUTES,
        "refresh_token_ttl_days": settings.REFRESH_TOKEN_TTL_DAYS,
    }
