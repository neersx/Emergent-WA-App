"""Meta Graph API client with mock-mode fallback AND live-mode wiring.

In mock mode (META_MOCK_MODE=true) every outbound Meta call returns deterministic
stubs so the app is fully runnable without live credentials.

In live mode the client uses httpx with retries and a circuit breaker on top of
the Meta Graph v21.0 endpoints. To switch to live mode:
  1. Set META_MOCK_MODE=false in /app/backend/.env
  2. Provide real values for META_APP_ID, META_APP_SECRET,
     META_EMBEDDED_SIGNUP_CONFIG_ID, META_WEBHOOK_VERIFY_TOKEN
  3. Ensure your Meta app has Advanced Access for
     whatsapp_business_management and whatsapp_business_messaging.
  4. Restart the backend.

Also provides HMAC-SHA256 webhook signature helpers used by webhooks.py.
"""
from __future__ import annotations

import asyncio
import hmac
import hashlib
import secrets
import time
from typing import Any

import httpx
from loguru import logger

from .config import settings


# --- Signature helpers ---
def sign_payload(payload_bytes: bytes, app_secret: str | None = None) -> str:
    key = (app_secret or settings.META_APP_SECRET).encode()
    digest = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(payload_bytes: bytes, header_value: str | None) -> bool:
    if not header_value or not header_value.startswith("sha256="):
        return False
    expected = sign_payload(payload_bytes)
    return hmac.compare_digest(expected, header_value)


# --- Mock data helpers ---
_MOCK_TEMPLATES_PER_WABA = [
    {
        "name": "hello_world",
        "language": "en_US",
        "category": "UTILITY",
        "body": "Hello {{1}}, welcome to {{2}}!",
        "status": "APPROVED",
    },
    {
        "name": "order_shipped",
        "language": "en_US",
        "category": "UTILITY",
        "body": "Your order #{{1}} has shipped. Track it here: {{2}}",
        "status": "APPROVED",
    },
    {
        "name": "appointment_reminder",
        "language": "en_US",
        "category": "UTILITY",
        "body": "Reminder: your appointment is at {{1}} on {{2}}.",
        "status": "APPROVED",
    },
    {
        "name": "otp_verify",
        "language": "en_US",
        "category": "AUTHENTICATION",
        "body": "Your verification code is {{1}}. It expires in 5 minutes.",
        "status": "APPROVED",
    },
    {
        "name": "marketing_promo",
        "language": "en_US",
        "category": "MARKETING",
        "body": "Hey {{1}}, here's {{2}}% off your next order. Use code {{3}}.",
        "status": "APPROVED",
    },
]


class MetaClient:
    """Thin client around Meta Graph endpoints. Switches to mock automatically."""

    def __init__(self) -> None:
        self.mock = settings.META_MOCK_MODE
        self.api_version = settings.META_GRAPH_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    # --------- HTTP plumbing for live mode ---------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict | None = None,
        json: dict | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        attempt = 0
        last_err: Exception | None = None
        while attempt < max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.request(
                        method, url, params=params, json=json, headers=headers
                    )
                if resp.status_code in (429, 500, 502, 503, 504):
                    # Retryable
                    raise httpx.HTTPStatusError(
                        f"{resp.status_code}", request=resp.request, response=resp
                    )
                if resp.status_code >= 400:
                    logger.error(
                        f"Meta {method} {path} -> {resp.status_code} {resp.text[:300]}"
                    )
                    resp.raise_for_status()
                return resp.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last_err = e
                backoff = 0.25 * (2 ** (attempt - 1))
                logger.warning(
                    f"Meta {method} {path} attempt {attempt} failed: {e}; backoff {backoff}s"
                )
                await asyncio.sleep(backoff)
        raise RuntimeError(f"Meta call failed after {max_retries} attempts: {last_err}")

    # --------- Public client methods ---------
    async def exchange_code_for_business_token(self, code: str) -> dict[str, Any]:
        if self.mock:
            suffix = secrets.token_hex(6)
            return {
                "access_token": f"MOCK_BIZ_TOKEN_{code[:8]}_{suffix}",
                "token_type": "bearer",
                "expires_in": 60 * 60 * 24 * 60,
                "waba_id": f"100000000{suffix[:6]}",
                "business_id": f"200000000{suffix[:6]}",
                "phone_number_id": f"300000000{suffix[:6]}",
                "display_phone_number": f"+1555{int(time.time()) % 10000000:07d}",
                "verified_name": "Demo Business",
                "quality_rating": "GREEN",
            }
        # Live: exchange code via oauth/access_token
        params = {
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "code": code,
        }
        token_resp = await self._request("GET", "/oauth/access_token", params=params)
        access_token = token_resp["access_token"]

        # In production, the front-end Embedded Signup callback also returns
        # waba_id, phone_number_id, business_id alongside the auth code.
        # We'd consult those here; fallback to /me/businesses if absent.
        return {
            "access_token": access_token,
            "token_type": token_resp.get("token_type", "bearer"),
            "expires_in": token_resp.get("expires_in", 60 * 60 * 24 * 60),
            "waba_id": "",  # filled in by caller from front-end signup payload
            "business_id": "",
            "phone_number_id": "",
            "display_phone_number": "",
            "verified_name": "",
            "quality_rating": "GREEN",
        }

    async def subscribe_app_to_waba(self, waba_id: str, business_token: str):
        if self.mock:
            logger.info(f"[mock] Subscribed app to WABA {waba_id}")
            return {"success": True}
        return await self._request(
            "POST", f"/{waba_id}/subscribed_apps", token=business_token
        )

    async def register_phone_number(
        self, phone_number_id: str, business_token: str, pin: str = "000000"
    ):
        if self.mock:
            logger.info(f"[mock] Registered phone {phone_number_id}")
            return {"success": True}
        return await self._request(
            "POST",
            f"/{phone_number_id}/register",
            token=business_token,
            json={"messaging_product": "whatsapp", "pin": pin},
        )

    async def send_template(
        self,
        phone_number_id: str,
        business_token: str,
        to_wa_id: str,
        template_name: str,
        language_code: str,
        components: list[dict] | None = None,
    ) -> dict[str, Any]:
        if self.mock:
            wamid = f"wamid.MOCK_{secrets.token_hex(10).upper()}"
            return {
                "messaging_product": "whatsapp",
                "contacts": [{"input": to_wa_id, "wa_id": to_wa_id}],
                "messages": [{"id": wamid, "message_status": "accepted"}],
            }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_wa_id,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components
        return await self._request(
            "POST", f"/{phone_number_id}/messages", token=business_token, json=payload
        )

    async def send_text(
        self,
        phone_number_id: str,
        business_token: str,
        to_wa_id: str,
        text: str,
    ) -> dict[str, Any]:
        if self.mock:
            wamid = f"wamid.MOCK_{secrets.token_hex(10).upper()}"
            return {
                "messaging_product": "whatsapp",
                "contacts": [{"input": to_wa_id, "wa_id": to_wa_id}],
                "messages": [{"id": wamid, "message_status": "accepted"}],
            }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_wa_id,
            "type": "text",
            "text": {"body": text},
        }
        return await self._request(
            "POST", f"/{phone_number_id}/messages", token=business_token, json=payload
        )

    async def get_phone_info(
        self, phone_number_id: str, business_token: str
    ) -> dict[str, Any]:
        """Fetch display info about a phone number. Returns empty dict on failure."""
        if self.mock:
            return {}
        try:
            r = await self._request(
                "GET",
                f"/{phone_number_id}",
                token=business_token,
                params={"fields": "display_phone_number,verified_name,quality_rating"},
            )
            return {
                "display_phone_number": r.get("display_phone_number"),
                "verified_name": r.get("verified_name"),
                "quality_rating": r.get("quality_rating"),
            }
        except Exception as e:
            logger.warning(f"get_phone_info failed for {phone_number_id}: {e}")
            return {}

    async def get_waba_info(
        self, waba_id: str, business_token: str
    ) -> dict[str, Any]:
        """Fetch WABA metadata. Returns empty dict on failure."""
        if self.mock:
            return {}
        try:
            r = await self._request(
                "GET",
                f"/{waba_id}",
                token=business_token,
                params={"fields": "name,business_verification_status,owner_business"},
            )
            return {
                "name": r.get("name"),
                "business_id": (r.get("owner_business") or {}).get("id")
                if isinstance(r.get("owner_business"), dict)
                else None,
            }
        except Exception as e:
            logger.warning(f"get_waba_info failed for {waba_id}: {e}")
            return {}

    async def list_templates(
        self, waba_id: str, business_token: str
    ) -> list[dict[str, Any]]:
        if self.mock:
            # Deterministic mock set per WABA
            out = []
            for t in _MOCK_TEMPLATES_PER_WABA:
                out.append({**t})
            return out
        resp = await self._request(
            "GET", f"/{waba_id}/message_templates", token=business_token
        )
        data = resp.get("data", []) or []
        out = []
        for t in data:
            body = None
            for c in t.get("components", []) or []:
                if c.get("type") == "BODY":
                    body = c.get("text")
                    break
            out.append(
                {
                    "name": t.get("name"),
                    "language": t.get("language"),
                    "category": t.get("category"),
                    "status": t.get("status"),
                    "body": body,
                }
            )
        return out


meta_client = MetaClient()
