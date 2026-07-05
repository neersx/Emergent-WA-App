"""Pydantic models for API + DB documents.

All DB documents use string UUID `id` as primary key. We never use Mongo `_id`
in Pydantic models (we set `_id` = `id` at insert time so the collection is keyed
by UUID).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    PlatformSuperAdmin = "PlatformSuperAdmin"
    TenantOwner = "TenantOwner"
    TenantAdmin = "TenantAdmin"
    Agent = "Agent"
    Viewer = "Viewer"


class MessageStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"


class MessageDirection(str, Enum):
    outbound = "outbound"
    inbound = "inbound"


# ---------- Auth requests ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tenant_name: str = Field(min_length=2, max_length=120)
    full_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = None


class MfaSetupVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class MfaDisableRequest(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=10)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# ---------- Auth responses ----------
class UserPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    role: Role
    full_name: str | None = None
    mfa_enabled: bool = False
    mfa_required: bool = False
    tenant_id: str | None = None
    tenant_name: str | None = None


class LoginResponse(BaseModel):
    user: UserPublic
    mfa_required: bool = False
    mfa_setup_required: bool = False


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_data_url: str


# ---------- Onboarding ----------
class EmbeddedSignupExchange(BaseModel):
    code: str
    waba_id: str | None = None
    phone_number_id: str | None = None
    business_id: str | None = None


# ---------- Messaging ----------
class TemplateComponent(BaseModel):
    type: Literal["header", "body", "footer", "button"]
    parameters: list[dict[str, Any]] = Field(default_factory=list)


class SendTemplateRequest(BaseModel):
    phone_number_id: str
    to_wa_id: str = Field(min_length=5, max_length=32)
    template_name: str = Field(min_length=1, max_length=120)
    language_code: str = Field(default="en_US", min_length=2, max_length=16)
    components: list[TemplateComponent] | None = None
    idempotency_key: str | None = Field(default=None, max_length=120)


class MessagePublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tenant_id: str
    phone_number_id: str
    direction: MessageDirection
    to_wa_id: str | None = None
    from_wa_id: str | None = None
    template_name: str | None = None
    language_code: str | None = None
    meta_message_id: str | None = None
    status: MessageStatus
    pricing_category: str | None = None
    pricing_billable: bool | None = None
    cost_amount: float | None = None
    cost_currency: str | None = None
    country_code: str | None = None
    error: str | None = None
    idempotency_key: str | None = None
    created_at: datetime
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    failed_at: datetime | None = None


# ---------- Simulate webhook (admin demo helper) ----------
class SimulateWebhookRequest(BaseModel):
    message_id: str
    event: Literal["sent", "delivered", "read", "failed"] = "delivered"


# ---------- WABA / Phone ----------
class WabaPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tenant_id: str
    waba_id: str
    business_id: str | None = None
    name: str | None = None
    created_at: datetime


class PhoneNumberPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tenant_id: str
    waba_id: str
    phone_number_id: str
    display_phone_number: str | None = None
    verified_name: str | None = None
    quality_rating: str | None = None
    created_at: datetime


# ---------- Phase 2: Template component builder ----------

class TemplateStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


class TemplateButtonType(str, Enum):
    QUICK_REPLY = "QUICK_REPLY"
    URL = "URL"
    PHONE_NUMBER = "PHONE_NUMBER"


class TemplateHeaderFormat(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    LOCATION = "LOCATION"


class TemplateButton(BaseModel):
    type: TemplateButtonType
    text: str = Field(min_length=1, max_length=25)
    url: str | None = Field(default=None, max_length=2000)
    phone_number: str | None = Field(default=None, max_length=20)
    url_example: str | None = None  # sample value for URL variable


class TemplateComponentSpec(BaseModel):
    type: Literal["HEADER", "BODY", "FOOTER", "BUTTONS"]
    format: TemplateHeaderFormat | None = None  # HEADER only
    text: str | None = Field(default=None, max_length=4096)
    buttons: list[TemplateButton] | None = None  # BUTTONS only
    example_header_text: list[str] | None = None
    example_body_text: list[list[str]] | None = None


class TemplateCreateFull(BaseModel):
    waba_id: str
    name: str = Field(min_length=1, max_length=512)
    language: str = Field(default="en_US", min_length=2, max_length=16)
    category: Literal["UTILITY", "MARKETING", "AUTHENTICATION"] = "UTILITY"
    components: list[TemplateComponentSpec]


# ---------- Phase 2: Inbox / Conversation ----------

class ConversationStatus(str, Enum):
    open = "open"
    closed = "closed"


class AssignConversationRequest(BaseModel):
    user_id: str | None = None  # None = unassign


class CloseConversationRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=256)
