"""Media download from Meta Graph + local storage + authenticated serving."""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger

from .config import settings

MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/app/media"))

router = APIRouter(prefix="/api/inbox/media", tags=["media"])

_MIME_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "video/mp4": "mp4",
    "video/3gpp": "3gp",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/aac": "aac",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


def mime_to_ext(mime: str | None) -> str:
    if not mime:
        return "bin"
    return _MIME_EXT.get(mime.split(";")[0].strip(), "bin")


def _sign(path: str, expires: int) -> str:
    key = settings.JWT_SIGNING_KEY.encode()
    msg = f"{path}:{expires}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:24]


def make_media_url(app_base_url: str, tenant_id: str, media_id: str, ext: str) -> str:
    """Return a signed 1-hour URL for serving a stored media file."""
    rel = f"{tenant_id}/{media_id}.{ext}"
    expires = int(time.time()) + 3600
    token = _sign(rel, expires)
    return f"{app_base_url}/api/inbox/media/{rel}?token={token}&expires={expires}"


async def download_and_store(
    media_id: str,
    tenant_id: str,
    business_token: str,
    mime_type: str,
    api_version: str = "v21.0",
) -> tuple[str | None, str]:
    """Download a Meta media file and store it locally.

    Returns (local_path_or_None, ext).
    """
    ext = mime_to_ext(mime_type)
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    tenant_dir = MEDIA_ROOT / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    dest = tenant_dir / f"{media_id}.{ext}"

    if dest.exists():
        return str(dest), ext  # idempotent

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Get download URL from Meta
            meta_resp = await client.get(
                f"https://graph.facebook.com/{api_version}/{media_id}",
                headers={"Authorization": f"Bearer {business_token}"},
            )
            meta_resp.raise_for_status()
            dl_url = meta_resp.json().get("url")
            if not dl_url:
                logger.warning(f"No download URL for media {media_id}")
                return None, ext

            # 2. Download binary
            bin_resp = await client.get(
                dl_url,
                headers={"Authorization": f"Bearer {business_token}"},
            )
            bin_resp.raise_for_status()
            content = bin_resp.content

        import asyncio
        await asyncio.to_thread(dest.write_bytes, content)
        logger.info(f"Stored media {media_id} ({len(content)}B) -> {dest}")
        return str(dest), ext

    except Exception as exc:
        logger.warning(f"Media download failed {media_id}: {exc}")
        return None, ext


@router.get("/{tenant_id}/{filename:path}")
async def serve_media(
    tenant_id: str,
    filename: str,
    token: str = Query(...),
    expires: int = Query(...),
):
    """Serve stored media. Requires a valid signed token."""
    if time.time() > expires:
        raise HTTPException(status_code=403, detail="Media URL expired")

    rel = f"{tenant_id}/{filename}"
    expected = _sign(rel, expires)
    if not hmac.compare_digest(token.ljust(24)[:24], expected):
        raise HTTPException(status_code=403, detail="Invalid media token")

    path = MEDIA_ROOT / tenant_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media not found")

    return FileResponse(str(path))
