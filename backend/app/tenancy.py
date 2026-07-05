"""Tenant-aware FastAPI dependencies + RBAC guards.

The Principal is the authenticated user with role + tenant context, derived from
the access token in the Authorization header (preferred) or `access_token` cookie.

Tenant isolation: every tenant-scoped query MUST be filtered by
`principal.tenant_id` server-side. The Principal helpers in this module are the
only approved source of `tenant_id`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import Cookie, Depends, Header, HTTPException, status
import jwt

from .auth import decode_access_token
from .models import Role


@dataclass
class Principal:
    user_id: str
    email: str
    role: Role
    tenant_id: str | None
    mfa_complete: bool

    @property
    def is_platform(self) -> bool:
        return self.role == Role.PlatformSuperAdmin


def _extract_token(
    authorization: str | None,
    access_token_cookie: str | None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if access_token_cookie:
        return access_token_cookie
    return None


async def get_principal(
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
) -> Principal:
    token = _extract_token(authorization, access_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    try:
        role = Role(payload["role"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role")
    return Principal(
        user_id=payload["sub"],
        email=payload["email"],
        role=role,
        tenant_id=payload.get("tenant_id"),
        mfa_complete=bool(payload.get("mfa_complete", False)),
    )


async def get_principal_mfa_complete(p: Principal = Depends(get_principal)) -> Principal:
    if not p.mfa_complete:
        # Special case: PlatformSuperAdmin without mfa_complete is blocked from everything
        # except MFA setup endpoints.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="MFA verification required"
        )
    return p


def require_roles(*roles: Role):
    allowed = set(roles)

    async def _guard(p: Principal = Depends(get_principal_mfa_complete)) -> Principal:
        if p.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return p

    return _guard


async def require_tenant(p: Principal = Depends(get_principal_mfa_complete)) -> Principal:
    """Ensure the principal is bound to a tenant (i.e. not a pure platform user)."""
    if not p.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required"
        )
    return p


def tenant_filter(p: Principal, extra: dict | None = None) -> dict:
    """Build a Mongo filter scoped to the principal's tenant."""
    f: dict = {"tenant_id": p.tenant_id}
    if extra:
        f.update(extra)
    return f
