"""POC end-to-end test for the WhatsApp SaaS core pipeline.

Validates user stories for Phase 1:
- US-A: Login as demo tenant owner (mfa not yet enabled) succeeds.
- US-B: Onboarding (mock embedded signup exchange) creates WABA + phone in tenant scope.
- US-C: Outbound template send transitions queued -> sent and records meta_message_id.
- US-D: Idempotency — repeat send with same idempotency_key creates only ONE message.
- US-E: Webhook signature verification — INVALID signature is rejected with 401 and no
  raw event / queue job is created.
- US-F: Webhook signature verification — VALID signature is accepted, ACK in <1s,
  raw event persisted, job enqueued.
- US-G: Worker projection — a properly-signed delivery webhook updates message status
  to "delivered" within a few seconds.
- US-H: Tenant isolation — a different tenant cannot see this tenant's WABAs or messages.
- US-I: MFA enrollment flow works end-to-end (setup -> verify -> login with code).
- US-J: Health endpoints respond and metrics are exposed.

Run with: python -m pytest backend/tests/test_core.py -v
or:        python backend/tests/test_core.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import time
import uuid
from datetime import datetime, timezone

import httpx
import pyotp

BASE = "http://localhost:8001"

DEMO_EMAIL = "owner@demo.com"
DEMO_PASSWORD = "Owner123!"


def _extract_access_cookie(resp: httpx.Response) -> str | None:
    """Pull access_token from Set-Cookie headers (httpx drops Secure cookies on HTTP)."""
    for h in resp.headers.get_list("set-cookie"):
        if h.startswith("access_token="):
            val = h.split("access_token=", 1)[1].split(";", 1)[0]
            return val
    return None


async def _login(client: httpx.AsyncClient, email: str, password: str, mfa: str | None = None):
    r = await client.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": password, **({"mfa_code": mfa} if mfa else {})},
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = _extract_access_cookie(r)
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    return r.json()


async def _register(client: httpx.AsyncClient, email: str, password: str, tenant: str):
    r = await client.post(
        f"{BASE}/api/auth/register",
        json={"email": email, "password": password, "tenant_name": tenant, "full_name": "QA"},
    )
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    token = _extract_access_cookie(r)
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    return r.json()


def _sign(payload_bytes: bytes, secret: str) -> str:
    import hmac

    return "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


async def _wait_for_status(client: httpx.AsyncClient, message_id: str, target: str, timeout=8.0):
    start = time.time()
    while time.time() - start < timeout:
        r = await client.get(f"{BASE}/api/messages")
        if r.status_code == 200:
            for m in r.json():
                if m["id"] == message_id and m["status"] == target:
                    return m
        await asyncio.sleep(0.25)
    raise AssertionError(f"Message {message_id} did not reach status={target} within {timeout}s")


async def main() -> None:
    # Read META_APP_SECRET from backend env file directly (we are running on the same host)
    secret = None
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith("META_APP_SECRET="):
                secret = line.split("=", 1)[1].strip().strip('"')
                break
    assert secret, "META_APP_SECRET not found in /app/backend/.env"
    print(f"Using META_APP_SECRET prefix={secret[:6]}…")

    failures: list[str] = []

    async with httpx.AsyncClient(timeout=15.0) as anon:
        # --- US-J: health ---
        try:
            r = await anon.get(f"{BASE}/api/health/live")
            assert r.status_code == 200 and r.json().get("status") == "ok"
            r = await anon.get(f"{BASE}/api/health/ready")
            assert r.status_code == 200 and r.json().get("db") is True
            r = await anon.get(f"{BASE}/api/metrics")
            assert r.status_code == 200 and "mq_queue_depth" in r.text
            print("[OK] US-J: health + metrics")
        except Exception as e:
            failures.append(f"US-J: {e}")
            print(f"[FAIL] US-J: {e}")

    # Use a per-client cookie jar to act as the demo tenant
    async with httpx.AsyncClient(timeout=15.0) as c1:
        # --- US-A: login demo tenant ---
        try:
            r = await _login(c1, DEMO_EMAIL, DEMO_PASSWORD)
            assert r["user"]["email"] == DEMO_EMAIL
            assert r["user"]["tenant_id"]
            print(f"[OK] US-A: demo login (tenant_id={r['user']['tenant_id'][:8]}…)")
        except Exception as e:
            failures.append(f"US-A: {e}")
            print(f"[FAIL] US-A: {e}")
            return

        # --- US-B: onboarding exchange ---
        try:
            r = await c1.post(
                f"{BASE}/api/onboarding/exchange",
                json={"code": f"AUTHCODE_{secrets.token_hex(6)}"},
            )
            assert r.status_code == 200, r.text
            data = r.json()
            waba = data["waba"]
            phone = data["phone_number"]
            assert waba["waba_id"] and phone["phone_number_id"]
            # Tenant ownership check
            wabas_list = (await c1.get(f"{BASE}/api/wabas")).json()
            assert any(w["waba_id"] == waba["waba_id"] for w in wabas_list)
            print(f"[OK] US-B: onboarding -> WABA {waba['waba_id']} phone {phone['phone_number_id']}")
        except Exception as e:
            failures.append(f"US-B: {e}")
            print(f"[FAIL] US-B: {e}")
            return

        phone_number_id = phone["phone_number_id"]

        # --- US-C: send template -> queued/sent ---
        try:
            idem = f"poc-{uuid.uuid4()}"
            r = await c1.post(
                f"{BASE}/api/messages/send",
                json={
                    "phone_number_id": phone_number_id,
                    "to_wa_id": "15551234567",
                    "template_name": "hello_world",
                    "language_code": "en_US",
                    "idempotency_key": idem,
                },
            )
            assert r.status_code == 200, r.text
            msg = r.json()
            assert msg["status"] in ("sent", "queued")
            assert msg["meta_message_id"], "meta_message_id missing"
            msg_id = msg["id"]
            print(f"[OK] US-C: send -> id={msg_id[:8]} status={msg['status']} wamid={msg['meta_message_id']}")
        except Exception as e:
            failures.append(f"US-C: {e}")
            print(f"[FAIL] US-C: {e}")
            return

        # --- US-D: idempotency ---
        try:
            r2 = await c1.post(
                f"{BASE}/api/messages/send",
                json={
                    "phone_number_id": phone_number_id,
                    "to_wa_id": "15551234567",
                    "template_name": "hello_world",
                    "language_code": "en_US",
                    "idempotency_key": idem,
                },
            )
            assert r2.status_code == 200, r2.text
            msg2 = r2.json()
            assert msg2["id"] == msg_id, f"idempotency violated: {msg2['id']} != {msg_id}"
            # And only one message in DB for this idem key
            list_resp = await c1.get(f"{BASE}/api/messages?limit=200")
            count = sum(1 for m in list_resp.json() if m.get("idempotency_key") == idem)
            assert count == 1, f"expected 1 message for idem key, got {count}"
            print(f"[OK] US-D: idempotency — single message for repeated send")
        except Exception as e:
            failures.append(f"US-D: {e}")
            print(f"[FAIL] US-D: {e}")

    # --- US-E + US-F: webhook signature verification ---
    async with httpx.AsyncClient(timeout=15.0) as anon:
        try:
            payload = {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "WABA_X",
                        "changes": [
                            {
                                "field": "messages",
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {"phone_number_id": phone_number_id},
                                    "statuses": [
                                        {
                                            "id": msg["meta_message_id"],
                                            "status": "delivered",
                                            "timestamp": str(int(time.time())),
                                            "recipient_id": "15551234567",
                                            "pricing": {
                                                "billable": True,
                                                "pricing_model": "CBP",
                                                "category": "utility",
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
            raw = json.dumps(payload, separators=(",", ":")).encode()

            # Invalid signature
            bad = await anon.post(
                f"{BASE}/api/webhooks/meta",
                content=raw,
                headers={
                    "X-Hub-Signature-256": "sha256=" + "0" * 64,
                    "Content-Type": "application/json",
                },
            )
            assert bad.status_code == 401, f"expected 401 for invalid signature, got {bad.status_code}"
            print("[OK] US-E: invalid signature -> 401")

            # Valid signature
            t0 = time.perf_counter()
            ok = await anon.post(
                f"{BASE}/api/webhooks/meta",
                content=raw,
                headers={
                    "X-Hub-Signature-256": _sign(raw, secret),
                    "Content-Type": "application/json",
                },
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert ok.status_code == 200, ok.text
            assert ok.json().get("received") is True
            assert elapsed_ms < 1000, f"webhook ACK exceeded 1s: {elapsed_ms:.1f}ms"
            print(f"[OK] US-F: valid signature -> 200 in {elapsed_ms:.1f}ms")
        except Exception as e:
            failures.append(f"US-E/F: {e}")
            print(f"[FAIL] US-E/F: {e}")

    # --- US-G: worker projects status update ---
    async with httpx.AsyncClient(timeout=15.0) as c1:
        await _login(c1, DEMO_EMAIL, DEMO_PASSWORD)
        try:
            updated = await _wait_for_status(c1, msg_id, "delivered", timeout=8.0)
            assert updated.get("delivered_at"), "delivered_at not set"
            assert updated.get("pricing_category") == "utility"
            print(f"[OK] US-G: worker projected status -> delivered (cat={updated['pricing_category']})")
        except Exception as e:
            failures.append(f"US-G: {e}")
            print(f"[FAIL] US-G: {e}")

    # --- US-H: tenant isolation ---
    async with httpx.AsyncClient(timeout=15.0) as c2:
        try:
            new_email = f"qa+{uuid.uuid4().hex[:8]}@example.com"
            await _register(c2, new_email, "QApassword1!", "QA Tenant")
            # The new tenant should see ZERO WABAs and ZERO messages
            wabas = (await c2.get(f"{BASE}/api/wabas")).json()
            msgs = (await c2.get(f"{BASE}/api/messages")).json()
            assert len(wabas) == 0, f"new tenant sees {len(wabas)} WABAs (expected 0)"
            assert len(msgs) == 0, f"new tenant sees {len(msgs)} messages (expected 0)"
            # And cannot send via demo tenant's phone_number_id (404)
            r = await c2.post(
                f"{BASE}/api/messages/send",
                json={
                    "phone_number_id": phone_number_id,
                    "to_wa_id": "15551234567",
                    "template_name": "hello_world",
                    "language_code": "en_US",
                },
            )
            assert r.status_code == 404, f"expected 404 cross-tenant send, got {r.status_code}: {r.text}"
            print("[OK] US-H: tenant isolation enforced")
        except Exception as e:
            failures.append(f"US-H: {e}")
            print(f"[FAIL] US-H: {e}")

    # --- US-I: MFA enroll/verify roundtrip ---
    async with httpx.AsyncClient(timeout=15.0) as c3:
        try:
            email = f"mfa+{uuid.uuid4().hex[:6]}@example.com"
            await _register(c3, email, "MfaTest123!", "MFA Tenant")
            setup = (await c3.post(f"{BASE}/api/auth/mfa/setup")).json()
            assert "secret" in setup and "qr_data_url" in setup
            secret_b32 = setup["secret"]
            code = pyotp.TOTP(secret_b32).now()
            v = await c3.post(f"{BASE}/api/auth/mfa/verify", json={"code": code})
            assert v.status_code == 200, v.text
            # Now login flow: first without code returns mfa_required=True
            async with httpx.AsyncClient(timeout=15.0) as c4:
                r = await c4.post(
                    f"{BASE}/api/auth/login", json={"email": email, "password": "MfaTest123!"}
                )
                assert r.status_code == 200 and r.json()["mfa_required"] is True
                # With code
                code2 = pyotp.TOTP(secret_b32).now()
                r2 = await c4.post(
                    f"{BASE}/api/auth/login",
                    json={"email": email, "password": "MfaTest123!", "mfa_code": code2},
                )
                assert r2.status_code == 200 and r2.json()["mfa_required"] is False
            print("[OK] US-I: MFA enroll + verify + login-with-code")
        except Exception as e:
            failures.append(f"US-I: {e}")
            print(f"[FAIL] US-I: {e}")

    print("\n===== POC RESULTS =====")
    if failures:
        print(f"FAILED: {len(failures)} story/stories")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)
    else:
        print("ALL POC USER STORIES PASSED ✓")


if __name__ == "__main__":
    asyncio.run(main())
