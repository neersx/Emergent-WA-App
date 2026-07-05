"""Health + Prometheus metrics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from .db import get_db
from .queue import queue_depth

router = APIRouter(prefix="/api", tags=["health"])

registry = CollectorRegistry()
webhook_received = Counter(
    "meta_webhooks_received_total", "Webhook events received", registry=registry
)
webhook_invalid_sig = Counter(
    "meta_webhooks_invalid_signature_total", "Invalid signature rejections", registry=registry
)
messages_sent = Counter(
    "meta_messages_sent_total", "Outbound template sends accepted", registry=registry
)
request_latency = Histogram(
    "http_request_latency_seconds", "Request latency", registry=registry
)
queue_size_gauge = Gauge(
    "mq_queue_depth", "Background queue depth", ["status"], registry=registry
)


@router.get("/health/live")
async def live():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready():
    out = {"db": False, "queue": True}
    try:
        await get_db().command("ping")
        out["db"] = True
    except Exception:
        out["db"] = False
    out["status"] = "ok" if all([out["db"], out["queue"]]) else "degraded"
    return out


@router.get("/metrics")
async def metrics():
    # Refresh queue depth gauge
    try:
        depths = await queue_depth()
        for k, v in depths.items():
            queue_size_gauge.labels(status=k).set(v)
    except Exception:
        pass
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
