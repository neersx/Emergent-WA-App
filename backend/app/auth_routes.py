"""Auth routes: register, login, logout, refresh, MFA setup/verify, password reset."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from loguru import logger

from .auth import (
    consume_password_reset,
    create_password_reset,
    decrypt_mfa_secret,
    encrypt_mfa_secret,
    generate_mfa_secret,
    hash_password,
    issue_access_token,
    issue_refresh_token,
    otpauth_uri,
    qr_data_url_for,
    rotate_refresh_token,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    verify_password,
    verify_totp,
)
from .db import get_db
from .models import (
    LoginRequest,
    LoginResponse,
    MfaDisableRequest,
    MfaSetupResponse,
    MfaSetupVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    Role,
    UserPublic,
)
from .tenancy import Principal, get_principal

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
ACCESS_COOKIE = "access_token"
# Use SameSite=None + Secure so cookies work cross-site (preview iframe). We rely
# on httpOnly + CSRF-safe POST patterns + tenant guards.
COOKIE_KWARGS = dict(httponly=True, secure=True, samesite="none", path="/")


def _set_auth_cookies(resp: Response, access: str, refresh: str) -> None:
    resp.set_cookie(ACCESS_COOKIE, access, max_age=60 * 15, **COOKIE_KWARGS)
    resp.set_cookie(REFRESH_COOKIE, refresh, max_age=60 * 60 * 24 * 14, **COOKIE_KWARGS)


def _clear_auth_cookies(resp: Response) -> None:
    resp.delete_cookie(ACCESS_COOKIE, path="/")
    resp.delete_cookie(REFRESH_COOKIE, path="/")


def _user_public(u: dict, tenant_name: str | None = None) -> UserPublic:
    return UserPublic(
        id=u["_id"],
        email=u["email"],
        role=Role(u["role"]),
        full_name=u.get("full_name"),
        mfa_enabled=bool(u.get("mfa_enabled", False)),
        mfa_required=bool(u.get("mfa_required", False)),
        tenant_id=u.get("tenant_id"),
        tenant_name=tenant_name,
    )


@router.post("/register", response_model=LoginResponse)
async def register(body: RegisterRequest, response: Response):
    db = get_db()
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.tenants.insert_one(
        {
            "_id": tenant_id,
            "id": tenant_id,
            "name": body.tenant_name,
            "created_at": now,
        }
    )
    user_doc = {
        "_id": user_id,
        "id": user_id,
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "full_name": body.full_name,
        "role": Role.TenantOwner.value,
        "tenant_id": tenant_id,
        "mfa_enabled": False,
        "mfa_required": False,
        "mfa_secret_encrypted": None,
        "created_at": now,
    }
    await db.users.insert_one(user_doc)

    access = issue_access_token(
        user_id, user_doc["email"], Role.TenantOwner.value, tenant_id, mfa_complete=True
    )
    refresh = await issue_refresh_token(user_id)
    _set_auth_cookies(response, access, refresh)
    return LoginResponse(user=_user_public(user_doc, tenant_name=body.tenant_name))


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response):
    db = get_db()
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    mfa_required = bool(user.get("mfa_enabled")) or bool(user.get("mfa_required"))
    mfa_setup_required = bool(user.get("mfa_required")) and not bool(user.get("mfa_enabled"))

    if user.get("mfa_enabled"):
        if not body.mfa_code:
            # Issue a short-lived token with mfa_complete=False so user can call /mfa/verify
            access = issue_access_token(
                user["_id"], user["email"], user["role"], user.get("tenant_id"), mfa_complete=False
            )
            refresh = await issue_refresh_token(user["_id"])
            _set_auth_cookies(response, access, refresh)
            tenant_name = await _tenant_name(user.get("tenant_id"))
            return LoginResponse(
                user=_user_public(user, tenant_name=tenant_name),
                mfa_required=True,
            )
        secret = decrypt_mfa_secret(user["mfa_secret_encrypted"])
        if not verify_totp(secret, body.mfa_code):
            raise HTTPException(status_code=401, detail="Invalid MFA code")

    access = issue_access_token(
        user["_id"],
        user["email"],
        user["role"],
        user.get("tenant_id"),
        mfa_complete=not mfa_setup_required,
    )
    refresh = await issue_refresh_token(user["_id"])
    _set_auth_cookies(response, access, refresh)
    tenant_name = await _tenant_name(user.get("tenant_id"))
    return LoginResponse(
        user=_user_public(user, tenant_name=tenant_name),
        mfa_required=mfa_required and not user.get("mfa_enabled"),
        mfa_setup_required=mfa_setup_required,
    )


async def _tenant_name(tenant_id: str | None) -> str | None:
    if not tenant_id:
        return None
    t = await get_db().tenants.find_one({"_id": tenant_id})
    return t["name"] if t else None


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
):
    if refresh_token:
        await revoke_refresh_token(refresh_token)
    _clear_auth_cookies(response)
    return {"ok": True}


@router.post("/refresh", response_model=LoginResponse)
async def refresh(response: Response, refresh_token: str | None = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    result = await rotate_refresh_token(refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Refresh token invalid or expired")
    new_raw, user = result
    mfa_setup_required = bool(user.get("mfa_required")) and not bool(user.get("mfa_enabled"))
    access = issue_access_token(
        user["_id"], user["email"], user["role"], user.get("tenant_id"),
        mfa_complete=not (mfa_setup_required or user.get("mfa_enabled")),
    )
    _set_auth_cookies(response, access, new_raw)
    tenant_name = await _tenant_name(user.get("tenant_id"))
    return LoginResponse(user=_user_public(user, tenant_name=tenant_name))


@router.get("/me", response_model=UserPublic)
async def me(p: Principal = Depends(get_principal)):
    user = await get_db().users.find_one({"_id": p.user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    tenant_name = await _tenant_name(user.get("tenant_id"))
    return _user_public(user, tenant_name=tenant_name)


# ---------- MFA ----------
@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(p: Principal = Depends(get_principal)):
    """Generate a new TOTP secret + provisioning URI + QR code data URL.

    The secret is stored temporarily on the user as `mfa_secret_pending_encrypted`
    and only promoted to `mfa_secret_encrypted` on successful verification.
    """
    db = get_db()
    user = await db.users.find_one({"_id": p.user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    secret = generate_mfa_secret()
    uri = otpauth_uri(secret, user["email"])
    qr = qr_data_url_for(uri)
    await db.users.update_one(
        {"_id": p.user_id},
        {"$set": {"mfa_secret_pending_encrypted": encrypt_mfa_secret(secret)}},
    )
    return MfaSetupResponse(secret=secret, otpauth_uri=uri, qr_data_url=qr)


@router.post("/mfa/verify", response_model=LoginResponse)
async def mfa_verify(body: MfaSetupVerifyRequest, response: Response, p: Principal = Depends(get_principal)):
    db = get_db()
    user = await db.users.find_one({"_id": p.user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.get("mfa_enabled"):
        # Mid-login MFA verification path
        secret = decrypt_mfa_secret(user["mfa_secret_encrypted"])
        if not verify_totp(secret, body.code):
            raise HTTPException(status_code=401, detail="Invalid code")
    else:
        pending = user.get("mfa_secret_pending_encrypted")
        if not pending:
            raise HTTPException(status_code=400, detail="No MFA setup in progress")
        secret = decrypt_mfa_secret(pending)
        if not verify_totp(secret, body.code):
            raise HTTPException(status_code=401, detail="Invalid code")
        await db.users.update_one(
            {"_id": p.user_id},
            {
                "$set": {
                    "mfa_secret_encrypted": pending,
                    "mfa_enabled": True,
                },
                "$unset": {"mfa_secret_pending_encrypted": ""},
            },
        )
        user = await db.users.find_one({"_id": p.user_id})

    access = issue_access_token(
        user["_id"], user["email"], user["role"], user.get("tenant_id"), mfa_complete=True
    )
    refresh = await issue_refresh_token(user["_id"])
    _set_auth_cookies(response, access, refresh)
    tenant_name = await _tenant_name(user.get("tenant_id"))
    return LoginResponse(user=_user_public(user, tenant_name=tenant_name))


@router.post("/mfa/disable")
async def mfa_disable(body: MfaDisableRequest, p: Principal = Depends(get_principal)):
    db = get_db()
    user = await db.users.find_one({"_id": p.user_id})
    if not user or not user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA not enabled")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    secret = decrypt_mfa_secret(user["mfa_secret_encrypted"])
    if not verify_totp(secret, body.code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    if user.get("role") == Role.PlatformSuperAdmin.value:
        raise HTTPException(status_code=403, detail="Super-admins cannot disable MFA")
    await db.users.update_one(
        {"_id": p.user_id},
        {"$set": {"mfa_enabled": False}, "$unset": {"mfa_secret_encrypted": ""}},
    )
    return {"ok": True}


# ---------- Password reset ----------
@router.post("/password/forgot")
async def password_forgot(body: PasswordResetRequest):
    db = get_db()
    user = await db.users.find_one({"email": body.email.lower()})
    if user:
        raw = await create_password_reset(user["_id"])
        # Console log only (per user choice)
        logger.info(
            f"[email-mock] To: {user['email']}\n"
            f"Subject: Reset your WhatsApp SaaS password\n"
            f"Reset token: {raw}\n"
            f"(POST /api/auth/password/reset with this token + new_password)"
        )
    # Always return ok to avoid email enumeration
    return {"ok": True}


@router.post("/password/reset")
async def password_reset(body: PasswordResetConfirm):
    user_id = await consume_password_reset(body.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    await get_db().users.update_one(
        {"_id": user_id}, {"$set": {"password_hash": hash_password(body.new_password)}}
    )
    # Revoke all sessions on password change
    await revoke_all_refresh_tokens(user_id)
    return {"ok": True}
