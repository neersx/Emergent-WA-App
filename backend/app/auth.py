"""Authentication: password hashing, JWT, refresh tokens, MFA.

Design notes:
- Passwords hashed with bcrypt.
- Access tokens are short-lived JWTs (HS256) carrying user_id, tenant_id, role,
  email, mfa_complete claim.
- Refresh tokens are random opaque strings; only their sha256 hash is stored.
  Set as httpOnly Secure cookie. Rotated on every refresh; previous token revoked.
- MFA uses TOTP (pyotp). MFA secret is stored encrypted at rest.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Any

import bcrypt
import jwt
import pyotp
import qrcode

from .config import settings
from .crypto_utils import encrypt as enc, decrypt as dec
from .db import get_db


# ---------- Passwords ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


# ---------- JWT access tokens ----------
def issue_access_token(
    user_id: str,
    email: str,
    role: str,
    tenant_id: str | None,
    mfa_complete: bool,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "mfa_complete": mfa_complete,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SIGNING_KEY, algorithms=[settings.JWT_ALGORITHM])


# ---------- Refresh tokens ----------
def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


async def issue_refresh_token(user_id: str) -> str:
    raw = secrets.token_urlsafe(48)
    await get_db().refresh_tokens.insert_one(
        {
            "_id": secrets.token_hex(8),
            "user_id": user_id,
            "token_hash": _sha256(raw),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
            "revoked": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return raw


async def rotate_refresh_token(old_raw: str) -> tuple[str, dict] | None:
    """Atomically validate and revoke the old refresh token, then issue a new one.

    Returns (new_raw, user_doc) or None if invalid/expired/revoked.
    """
    db = get_db()
    old_hash = _sha256(old_raw)
    doc = await db.refresh_tokens.find_one_and_update(
        {"token_hash": old_hash, "revoked": False, "expires_at": {"$gt": datetime.now(timezone.utc)}},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not doc:
        return None
    user = await db.users.find_one({"_id": doc["user_id"]})
    if not user:
        return None
    new_raw = await issue_refresh_token(doc["user_id"])
    return new_raw, user


async def revoke_refresh_token(raw: str) -> None:
    await get_db().refresh_tokens.update_one(
        {"token_hash": _sha256(raw)}, {"$set": {"revoked": True}}
    )


async def revoke_all_refresh_tokens(user_id: str) -> None:
    await get_db().refresh_tokens.update_many({"user_id": user_id}, {"$set": {"revoked": True}})


# ---------- Password reset ----------
async def create_password_reset(user_id: str) -> str:
    raw = secrets.token_urlsafe(32)
    await get_db().password_resets.insert_one(
        {
            "_id": secrets.token_hex(8),
            "user_id": user_id,
            "token_hash": _sha256(raw),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
            "used": False,
        }
    )
    return raw


async def consume_password_reset(raw: str) -> str | None:
    db = get_db()
    doc = await db.password_resets.find_one_and_update(
        {
            "token_hash": _sha256(raw),
            "used": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        },
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}},
    )
    return doc["user_id"] if doc else None


# ---------- TOTP MFA ----------
def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def otpauth_uri(secret: str, email: str, issuer: str = "WhatsApp SaaS") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def qr_data_url_for(uri: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


# ---------- MFA secret storage helpers ----------
def encrypt_mfa_secret(secret: str) -> str:
    return enc(secret)


def decrypt_mfa_secret(encrypted: str) -> str:
    return dec(encrypted)
