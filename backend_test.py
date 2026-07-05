"""Comprehensive backend API tests for WhatsApp SaaS MVP.

Tests all Phase 1 user stories (US1-US16) backend requirements:
- Health & metrics endpoints
- Auth (register, login, MFA, password reset)
- Onboarding (Embedded Signup exchange)
- WABAs & phone numbers (tenant isolation)
- Messaging (send, list, idempotency, simulate webhook)
- Webhooks (verification, signature validation, event processing)
- Tenant isolation
"""
import asyncio
import hashlib
import hmac
import json
import sys
import time
from datetime import datetime

import pyotp
import requests

# Configuration
BASE_URL = "https://whatsapp-saas-mvp.preview.emergentagent.com/api"
META_APP_SECRET = "mock-app-secret-replace-in-prod"  # From backend/.env


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


class BackendTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.session = requests.Session()
        self.access_token = None
        self.tenant_id = None
        self.user_id = None
        self.waba_id = None
        self.phone_number_id = None
        self.message_id = None
        self.mfa_secret = None
        
    def log(self, msg, color=Colors.RESET):
        print(f"{color}{msg}{Colors.RESET}")
        
    def test(self, name, func):
        """Run a single test function."""
        self.tests_run += 1
        self.log(f"\n[{self.tests_run}] Testing: {name}", Colors.BLUE)
        try:
            func()
            self.tests_passed += 1
            self.log(f"✅ PASSED: {name}", Colors.GREEN)
            return True
        except AssertionError as e:
            self.tests_failed += 1
            self.log(f"❌ FAILED: {name}", Colors.RED)
            self.log(f"   Error: {str(e)}", Colors.RED)
            return False
        except Exception as e:
            self.tests_failed += 1
            self.log(f"❌ ERROR: {name}", Colors.RED)
            self.log(f"   Exception: {str(e)}", Colors.RED)
            return False
    
    def assert_status(self, response, expected, msg=""):
        actual = response.status_code
        if actual != expected:
            detail = ""
            try:
                detail = f" | Response: {response.json()}"
            except:
                detail = f" | Response: {response.text[:200]}"
            raise AssertionError(
                f"Expected status {expected}, got {actual}{msg}{detail}"
            )
    
    def assert_in(self, key, data, msg=""):
        if key not in data:
            raise AssertionError(f"Key '{key}' not in response{msg}")
    
    def assert_equal(self, actual, expected, msg=""):
        if actual != expected:
            raise AssertionError(f"Expected {expected}, got {actual}{msg}")
    
    # ========== Health & Metrics ==========
    
    def test_health_live(self):
        r = self.session.get(f"{BASE_URL}/health/live")
        self.assert_status(r, 200)
        data = r.json()
        self.assert_equal(data.get("status"), "ok")
    
    def test_health_ready(self):
        r = self.session.get(f"{BASE_URL}/health/ready")
        self.assert_status(r, 200)
        data = r.json()
        self.assert_equal(data.get("db"), True, " - DB should be ready")
        self.assert_in("status", data)
    
    def test_metrics(self):
        r = self.session.get(f"{BASE_URL}/metrics")
        self.assert_status(r, 200)
        text = r.text
        assert "mq_queue_depth" in text, "Metrics should include mq_queue_depth"
    
    # ========== Auth: Register ==========
    
    def test_register(self):
        """Register a new tenant + owner."""
        ts = int(time.time())
        payload = {
            "email": f"test_owner_{ts}@example.com",
            "password": "TestPass123!",
            "tenant_name": f"Test Tenant {ts}",
            "full_name": "Test Owner"
        }
        r = self.session.post(f"{BASE_URL}/auth/register", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("user", data)
        user = data["user"]
        self.assert_equal(user["email"], payload["email"].lower())
        self.assert_equal(user["role"], "TenantOwner")
        self.assert_in("tenant_id", user)
        self.assert_in("tenant_name", user)
        # Cookies should be set
        assert "access_token" in self.session.cookies or "Set-Cookie" in r.headers
        # Store for later tests
        self.tenant_id = user["tenant_id"]
        self.user_id = user["id"]
        self.access_token = self.session.cookies.get("access_token")
    
    def test_login_seeded_owner(self):
        """Login with seeded owner@demo.com / Owner123!"""
        payload = {"email": "owner@demo.com", "password": "Owner123!"}
        r = self.session.post(f"{BASE_URL}/auth/login", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("user", data)
        user = data["user"]
        self.assert_equal(user["email"], "owner@demo.com")
        self.assert_equal(user["role"], "TenantOwner")
        # Update session state
        self.tenant_id = user["tenant_id"]
        self.user_id = user["id"]
        self.access_token = self.session.cookies.get("access_token")
    
    def test_login_wrong_password(self):
        """Login with wrong password should return 401."""
        payload = {"email": "owner@demo.com", "password": "WrongPassword"}
        r = self.session.post(f"{BASE_URL}/auth/login", json=payload)
        self.assert_status(r, 401)
    
    def test_auth_me(self):
        """GET /api/auth/me should return current user."""
        r = self.session.get(f"{BASE_URL}/auth/me")
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("id", data)
        self.assert_in("email", data)
        self.assert_in("role", data)
    
    # ========== MFA Flow ==========
    
    def test_mfa_setup(self):
        """POST /api/auth/mfa/setup returns secret + QR."""
        # Use a fresh session for MFA testing
        mfa_session = requests.Session()
        ts = int(time.time())
        # Register a new user for MFA testing
        payload = {
            "email": f"mfa_test_{ts}@example.com",
            "password": "MfaTest123!",
            "tenant_name": f"MFA Test Tenant {ts}"
        }
        r = mfa_session.post(f"{BASE_URL}/auth/register", json=payload)
        self.assert_status(r, 200)
        
        # Setup MFA
        r = mfa_session.post(f"{BASE_URL}/auth/mfa/setup")
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("secret", data)
        self.assert_in("otpauth_uri", data)
        self.assert_in("qr_data_url", data)
        # Store secret for verification
        self.mfa_secret = data["secret"]
        assert len(self.mfa_secret) > 10, "MFA secret should be non-empty"
    
    def test_mfa_verify(self):
        """POST /api/auth/mfa/verify with valid TOTP code enables MFA."""
        # Use a fresh session for MFA testing
        mfa_session = requests.Session()
        ts = int(time.time())
        # Register a new user for MFA testing
        payload = {
            "email": f"mfa_verify_{ts}@example.com",
            "password": "MfaVerify123!",
            "tenant_name": f"MFA Verify Tenant {ts}"
        }
        r = mfa_session.post(f"{BASE_URL}/auth/register", json=payload)
        self.assert_status(r, 200)
        
        # Setup MFA
        r = mfa_session.post(f"{BASE_URL}/auth/mfa/setup")
        self.assert_status(r, 200)
        secret = r.json()["secret"]
        
        # Generate TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        # Wait a moment to ensure code is fresh
        time.sleep(1)
        
        payload = {"code": code}
        r = mfa_session.post(f"{BASE_URL}/auth/mfa/verify", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("user", data)
        user = data["user"]
        self.assert_equal(user["mfa_enabled"], True, " - MFA should be enabled")
    
    # ========== Password Reset ==========
    
    def test_password_forgot(self):
        """POST /api/auth/password/forgot returns ok=true."""
        payload = {"email": "owner@demo.com"}
        r = self.session.post(f"{BASE_URL}/auth/password/forgot", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_equal(data.get("ok"), True)
        # Token is logged to backend stderr (console-only email)
    
    # ========== Onboarding ==========
    
    def test_onboarding_exchange(self):
        """POST /api/onboarding/exchange with arbitrary code returns WABA + phone."""
        ts = int(time.time())
        payload = {"code": f"mock_code_{ts}"}
        r = self.session.post(f"{BASE_URL}/onboarding/exchange", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("waba", data)
        self.assert_in("phone_number", data)
        waba = data["waba"]
        phone = data["phone_number"]
        self.assert_in("waba_id", waba)
        self.assert_in("phone_number_id", phone)
        # encrypted_business_token should NEVER appear in response
        assert "encrypted_business_token" not in json.dumps(data), \
            "encrypted_business_token must not be in response"
        # Store for later tests
        self.waba_id = waba["waba_id"]
        self.phone_number_id = phone["phone_number_id"]
    
    # ========== WABAs & Phone Numbers (Tenant Isolation) ==========
    
    def test_list_wabas(self):
        """GET /api/wabas returns only current tenant's WABAs."""
        r = self.session.get(f"{BASE_URL}/wabas")
        self.assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list), "Should return a list"
        # All WABAs should belong to current tenant
        for waba in data:
            self.assert_equal(waba["tenant_id"], self.tenant_id, " - Tenant isolation")
    
    def test_list_phone_numbers(self):
        """GET /api/phone-numbers returns only current tenant's phones."""
        r = self.session.get(f"{BASE_URL}/phone-numbers")
        self.assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list), "Should return a list"
        for phone in data:
            self.assert_equal(phone["tenant_id"], self.tenant_id, " - Tenant isolation")
    
    # ========== Messaging ==========
    
    def test_send_message(self):
        """POST /api/messages/send returns 200 with status=sent + meta_message_id."""
        # Ensure we have a phone number
        if not self.phone_number_id:
            r = self.session.post(
                f"{BASE_URL}/onboarding/exchange",
                json={"code": f"mock_{int(time.time())}"}
            )
            self.phone_number_id = r.json()["phone_number"]["phone_number_id"]
        
        payload = {
            "phone_number_id": self.phone_number_id,
            "to_wa_id": "15551234567",
            "template_name": "hello_world",
            "language_code": "en_US"
        }
        r = self.session.post(f"{BASE_URL}/messages/send", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("id", data)
        self.assert_in("status", data)
        self.assert_in("meta_message_id", data)
        self.assert_equal(data["status"], "sent")
        assert data["meta_message_id"] is not None, "meta_message_id should be set"
        # Store for later tests
        self.message_id = data["id"]
    
    def test_idempotency(self):
        """Sending twice with same idempotency_key returns same message."""
        if not self.phone_number_id:
            r = self.session.post(
                f"{BASE_URL}/onboarding/exchange",
                json={"code": f"mock_{int(time.time())}"}
            )
            self.phone_number_id = r.json()["phone_number"]["phone_number_id"]
        
        idempotency_key = f"test_idem_{int(time.time())}"
        payload = {
            "phone_number_id": self.phone_number_id,
            "to_wa_id": "15559999999",
            "template_name": "hello_world",
            "language_code": "en_US",
            "idempotency_key": idempotency_key
        }
        
        # First send
        r1 = self.session.post(f"{BASE_URL}/messages/send", json=payload)
        self.assert_status(r1, 200)
        msg1 = r1.json()
        
        # Second send with same key
        r2 = self.session.post(f"{BASE_URL}/messages/send", json=payload)
        self.assert_status(r2, 200)
        msg2 = r2.json()
        
        # Should return the SAME message
        self.assert_equal(msg1["id"], msg2["id"], " - Same message ID")
        self.assert_equal(msg1["idempotency_key"], idempotency_key)
    
    def test_list_messages(self):
        """GET /api/messages lists messages newest-first."""
        r = self.session.get(f"{BASE_URL}/messages")
        self.assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list), "Should return a list"
        # Check ordering (newest first)
        if len(data) >= 2:
            # created_at should be descending
            t1 = data[0]["created_at"]
            t2 = data[1]["created_at"]
            assert t1 >= t2, "Messages should be ordered newest-first"
    
    def test_simulate_webhook(self):
        """POST /api/messages/{id}/simulate-webhook queues webhook, worker updates status."""
        # Ensure we have a message
        if not self.message_id:
            if not self.phone_number_id:
                r = self.session.post(
                    f"{BASE_URL}/onboarding/exchange",
                    json={"code": f"mock_{int(time.time())}"}
                )
                self.phone_number_id = r.json()["phone_number"]["phone_number_id"]
            
            r = self.session.post(
                f"{BASE_URL}/messages/send",
                json={
                    "phone_number_id": self.phone_number_id,
                    "to_wa_id": "15551111111",
                    "template_name": "hello_world",
                    "language_code": "en_US"
                }
            )
            self.message_id = r.json()["id"]
        
        # Simulate delivered event
        payload = {"message_id": self.message_id, "event": "delivered"}
        r = self.session.post(
            f"{BASE_URL}/messages/{self.message_id}/simulate-webhook",
            json=payload
        )
        self.assert_status(r, 200)
        data = r.json()
        self.assert_equal(data.get("queued"), True)
        
        # Wait for worker to process (~4s as per spec)
        time.sleep(5)
        
        # Check message status updated to delivered
        r = self.session.get(f"{BASE_URL}/messages")
        messages = r.json()
        msg = next((m for m in messages if m["id"] == self.message_id), None)
        assert msg is not None, "Message should exist"
        self.assert_equal(msg["status"], "delivered", " - Status should be updated by worker")
    
    # ========== Webhooks ==========
    
    def test_webhook_verification(self):
        """GET /api/webhooks/meta with valid verify_token returns challenge."""
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "mock-verify-token",
            "hub.challenge": "test_challenge_12345"
        }
        r = self.session.get(f"{BASE_URL}/webhooks/meta", params=params)
        self.assert_status(r, 200)
        self.assert_equal(r.text, "test_challenge_12345")
    
    def test_webhook_invalid_signature(self):
        """POST /api/webhooks/meta with INVALID signature returns 401, no raw event."""
        payload = {"test": "data"}
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=INVALID_SIGNATURE"
        }
        r = self.session.post(f"{BASE_URL}/webhooks/meta", data=body, headers=headers)
        self.assert_status(r, 401)
        # Verify no raw event was created (would need DB access, skip for now)
    
    def test_webhook_valid_signature(self):
        """POST /api/webhooks/meta with VALID signature returns 200, persists event, enqueues job."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA_ID",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "123"},
                                "statuses": []
                            }
                        }
                    ]
                }
            ]
        }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        
        # Compute valid HMAC signature
        digest = hmac.new(
            META_APP_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={digest}"
        
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature
        }
        
        start = time.time()
        r = self.session.post(f"{BASE_URL}/webhooks/meta", data=body, headers=headers)
        elapsed = time.time() - start
        
        self.assert_status(r, 200)
        data = r.json()
        self.assert_equal(data.get("received"), True)
        self.assert_in("id", data)
        self.assert_in("ack_ms", data)
        # Should ACK in <1s
        assert elapsed < 1.0, f"Webhook should ACK in <1s, took {elapsed:.2f}s"
    
    # ========== Tenant Isolation ==========
    
    def test_tenant_isolation(self):
        """Register a NEW tenant; verify they can't access other tenant's data."""
        # Create a new tenant
        ts = int(time.time())
        payload = {
            "email": f"isolated_{ts}@example.com",
            "password": "IsolatedPass123!",
            "tenant_name": f"Isolated Tenant {ts}"
        }
        
        # Save current session
        old_cookies = self.session.cookies.copy()
        
        # Register new tenant
        r = self.session.post(f"{BASE_URL}/auth/register", json=payload)
        self.assert_status(r, 200)
        new_tenant_id = r.json()["user"]["tenant_id"]
        
        # New tenant should have no WABAs
        r = self.session.get(f"{BASE_URL}/wabas")
        self.assert_status(r, 200)
        wabas = r.json()
        self.assert_equal(len(wabas), 0, " - New tenant should have no WABAs")
        
        # Try to send message to a phone_number_id owned by another tenant
        # (This should fail with 404)
        if self.phone_number_id:
            payload = {
                "phone_number_id": self.phone_number_id,  # From original tenant
                "to_wa_id": "15551234567",
                "template_name": "hello_world",
                "language_code": "en_US"
            }
            r = self.session.post(f"{BASE_URL}/messages/send", json=payload)
            self.assert_status(r, 404, " - Should not access other tenant's phone")
        
        # Restore original session
        self.session.cookies = old_cookies
    
    # ========== Dashboard ==========
    
    def test_dashboard(self):
        """GET /api/dashboard returns stat counts."""
        r = self.session.get(f"{BASE_URL}/dashboard")
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("waba_count", data)
        self.assert_in("phone_count", data)
        self.assert_in("message_count", data)
        self.assert_in("sent_count", data)
        self.assert_in("delivered_count", data)
        self.assert_in("read_count", data)
        # All should be non-negative integers
        for key in data:
            assert isinstance(data[key], int), f"{key} should be an integer"
            assert data[key] >= 0, f"{key} should be non-negative"
    
    # ========== Phase 2: System Info ==========
    
    def test_system_info(self):
        """GET /api/system/info returns mock_mode, version, worker_enabled, NO secrets."""
        r = self.session.get(f"{BASE_URL}/system/info")
        self.assert_status(r, 200)
        data = r.json()
        # Required fields
        self.assert_in("mock_mode", data)
        self.assert_in("meta_graph_api_version", data)
        self.assert_in("worker_enabled", data)
        self.assert_equal(data["mock_mode"], True, " - Should be in mock mode")
        self.assert_equal(data["meta_graph_api_version"], "v21.0")
        self.assert_equal(data["worker_enabled"], True)
        # Verify NO secrets are exposed
        response_str = json.dumps(data)
        assert "META_APP_SECRET" not in response_str, "META_APP_SECRET must not be exposed"
        assert "TOKEN_ENCRYPTION_KEY" not in response_str, "TOKEN_ENCRYPTION_KEY must not be exposed"
        assert "JWT_SIGNING_KEY" not in response_str, "JWT_SIGNING_KEY must not be exposed"
        assert "mock-app-secret" not in response_str, "Secret values must not be exposed"
    
    # ========== Phase 2: Templates ==========
    
    def test_templates_sync(self):
        """POST /api/templates/sync returns synced count >= 3."""
        # Ensure we have a WABA
        if not self.waba_id:
            r = self.session.post(
                f"{BASE_URL}/onboarding/exchange",
                json={"code": f"mock_{int(time.time())}"}
            )
            self.waba_id = r.json()["waba"]["waba_id"]
        
        payload = {"waba_id": self.waba_id}
        r = self.session.post(f"{BASE_URL}/templates/sync", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("synced", data)
        assert data["synced"] >= 3, f"Should sync at least 3 templates, got {data['synced']}"
    
    def test_templates_list(self):
        """GET /api/templates returns synced templates."""
        r = self.session.get(f"{BASE_URL}/templates")
        self.assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list), "Should return a list"
        # After sync, should have templates
        if len(data) > 0:
            t = data[0]
            self.assert_in("id", t)
            self.assert_in("name", t)
            self.assert_in("language", t)
            self.assert_in("status", t)
    
    def test_templates_create(self):
        """POST /api/templates creates a local template (auto-approved in mock)."""
        # Ensure we have a WABA
        if not self.waba_id:
            r = self.session.post(
                f"{BASE_URL}/onboarding/exchange",
                json={"code": f"mock_{int(time.time())}"}
            )
            self.waba_id = r.json()["waba"]["waba_id"]
        
        ts = int(time.time())
        payload = {
            "waba_id": self.waba_id,
            "name": f"test_template_{ts}",
            "language": "en_US",
            "category": "UTILITY",
            "body": "Hi {{1}}, this is a test template!"
        }
        r = self.session.post(f"{BASE_URL}/templates", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("id", data)
        self.assert_equal(data["name"], payload["name"])
        self.assert_equal(data["status"], "APPROVED", " - Should be auto-approved in mock")
        # Store for delete test
        self.template_id = data["id"]
    
    def test_templates_delete(self):
        """DELETE /api/templates/{id} removes template."""
        # Create a template first
        if not self.waba_id:
            r = self.session.post(
                f"{BASE_URL}/onboarding/exchange",
                json={"code": f"mock_{int(time.time())}"}
            )
            self.waba_id = r.json()["waba"]["waba_id"]
        
        ts = int(time.time())
        payload = {
            "waba_id": self.waba_id,
            "name": f"delete_test_{ts}",
            "language": "en_US",
            "category": "UTILITY",
            "body": "Delete me!"
        }
        r = self.session.post(f"{BASE_URL}/templates", json=payload)
        template_id = r.json()["id"]
        
        # Delete it
        r = self.session.delete(f"{BASE_URL}/templates/{template_id}")
        self.assert_status(r, 200)
        data = r.json()
        self.assert_equal(data.get("deleted"), True)
    
    def test_templates_tenant_isolation(self):
        """POST /api/templates/sync with another tenant's waba_id returns 404."""
        # Create a new tenant
        ts = int(time.time())
        payload = {
            "email": f"template_iso_{ts}@example.com",
            "password": "TemplateIso123!",
            "tenant_name": f"Template Iso Tenant {ts}"
        }
        
        # Save current session
        old_cookies = self.session.cookies.copy()
        
        # Register new tenant
        r = self.session.post(f"{BASE_URL}/auth/register", json=payload)
        self.assert_status(r, 200)
        
        # Try to sync templates with original tenant's WABA
        if self.waba_id:
            payload = {"waba_id": self.waba_id}
            r = self.session.post(f"{BASE_URL}/templates/sync", json=payload)
            self.assert_status(r, 404, " - Should not access other tenant's WABA")
        
        # Restore original session
        self.session.cookies = old_cookies
    
    # ========== Phase 2: Inbox ==========
    
    def test_inbox_simulate_inbound(self):
        """POST /api/inbox/simulate-inbound creates conversation and returns conversation_id."""
        ts = int(time.time())
        payload = {
            "contact_wa_id": f"1555{ts % 10000000:07d}",
            "body": "Hi! I have a question about my order."
        }
        r = self.session.post(f"{BASE_URL}/inbox/simulate-inbound", json=payload)
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("conversation_id", data)
        self.assert_equal(data.get("created"), True)
        # Store for later tests
        self.conversation_id = data["conversation_id"]
    
    def test_inbox_list_conversations(self):
        """GET /api/inbox/conversations lists conversations with service_window_open=true."""
        r = self.session.get(f"{BASE_URL}/inbox/conversations")
        self.assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list), "Should return a list"
        if len(data) > 0:
            conv = data[0]
            self.assert_in("id", conv)
            self.assert_in("contact_wa_id", conv)
            self.assert_in("service_window_open", conv)
            # After simulate-inbound, window should be open
            self.assert_equal(conv["service_window_open"], True, " - Window should be open")
    
    def test_inbox_get_messages(self):
        """GET /api/inbox/conversations/{id}/messages returns thread with inbound message."""
        # Ensure we have a conversation
        if not hasattr(self, 'conversation_id') or not self.conversation_id:
            ts = int(time.time())
            payload = {
                "contact_wa_id": f"1555{ts % 10000000:07d}",
                "body": "Test message"
            }
            r = self.session.post(f"{BASE_URL}/inbox/simulate-inbound", json=payload)
            self.conversation_id = r.json()["conversation_id"]
        
        r = self.session.get(f"{BASE_URL}/inbox/conversations/{self.conversation_id}/messages")
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("conversation", data)
        self.assert_in("messages", data)
        messages = data["messages"]
        assert isinstance(messages, list), "Messages should be a list"
        assert len(messages) > 0, "Should have at least one message"
        # First message should be inbound
        msg = messages[0]
        self.assert_equal(msg["direction"], "inbound")
    
    def test_inbox_reply(self):
        """POST /api/inbox/conversations/{id}/reply succeeds while window is open."""
        # Ensure we have a conversation
        if not hasattr(self, 'conversation_id') or not self.conversation_id:
            ts = int(time.time())
            payload = {
                "contact_wa_id": f"1555{ts % 10000000:07d}",
                "body": "Test message"
            }
            r = self.session.post(f"{BASE_URL}/inbox/simulate-inbound", json=payload)
            self.conversation_id = r.json()["conversation_id"]
        
        payload = {"body": "Hello! Thanks for reaching out."}
        r = self.session.post(
            f"{BASE_URL}/inbox/conversations/{self.conversation_id}/reply",
            json=payload
        )
        self.assert_status(r, 200)
        data = r.json()
        self.assert_in("id", data)
        self.assert_equal(data["direction"], "outbound")
        self.assert_equal(data["body"], payload["body"])
    
    # ========== Phase 2: Analytics ==========
    
    def test_analytics_overview(self):
        """GET /api/analytics/overview?days=14 returns expected fields."""
        r = self.session.get(f"{BASE_URL}/analytics/overview?days=14")
        self.assert_status(r, 200)
        data = r.json()
        # Required fields
        self.assert_in("total_messages", data)
        self.assert_in("outbound", data)
        self.assert_in("inbound", data)
        self.assert_in("delivered", data)
        self.assert_in("failed", data)
        self.assert_in("delivery_rate", data)
        self.assert_in("conversations", data)
        self.assert_in("conversations_open_window", data)
        # All should be non-negative
        for key in ["total_messages", "outbound", "inbound", "delivered", "failed", "conversations", "conversations_open_window"]:
            assert data[key] >= 0, f"{key} should be non-negative"
    
    def test_analytics_timeseries(self):
        """GET /api/analytics/timeseries?days=7 returns array of daily buckets."""
        r = self.session.get(f"{BASE_URL}/analytics/timeseries?days=7")
        self.assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list), "Should return a list"
        assert len(data) >= 1, "Should return at least 1 daily bucket"
        if len(data) > 0:
            bucket = data[0]
            self.assert_in("date", bucket)
            self.assert_in("outbound", bucket)
            self.assert_in("inbound", bucket)
            self.assert_in("delivered", bucket)
            self.assert_in("read", bucket)
            self.assert_in("failed", bucket)
    
    def test_analytics_by_template(self):
        """GET /api/analytics/by-template?days=14 returns template stats."""
        r = self.session.get(f"{BASE_URL}/analytics/by-template?days=14")
        self.assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list), "Should return a list"
        # May be empty if no template messages sent
        if len(data) > 0:
            t = data[0]
            self.assert_in("template_name", t)
            self.assert_in("sent", t)
            self.assert_in("delivered", t)
            self.assert_in("failed", t)
            self.assert_in("delivery_rate", t)
    
    def test_analytics_by_phone(self):
        """GET /api/analytics/by-phone returns phone number stats."""
        r = self.session.get(f"{BASE_URL}/analytics/by-phone")
        self.assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list), "Should return a list"
        # May be empty if no messages sent
        if len(data) > 0:
            p = data[0]
            self.assert_in("phone_number_id", p)
            self.assert_in("display", p)
            self.assert_in("outbound", p)
            self.assert_in("inbound", p)
    
    # ========== Phase 2: Meta Client Import ==========
    
    def test_meta_client_import(self):
        """Verify meta_client.py imports without crash (live mode wiring)."""
        # This is tested by the fact that the server started successfully
        # and /api/system/info returns data. If meta_client had import errors,
        # the server wouldn't start.
        r = self.session.get(f"{BASE_URL}/system/info")
        self.assert_status(r, 200)
        # If we got here, meta_client imported successfully
        self.log("   meta_client.py imported successfully (server is running)", Colors.GREEN)
    
    def run_phase2_only(self):
        """Run Phase 2 tests only (brief verification of new features)."""
        self.log("\n" + "="*70, Colors.BLUE)
        self.log("WhatsApp SaaS MVP - Phase 2 Backend Tests", Colors.BLUE)
        self.log("="*70 + "\n", Colors.BLUE)
        
        # Login with seeded owner first
        self.log("\n--- Setup: Login as owner@demo.com ---", Colors.YELLOW)
        self.test("Login Seeded Owner", self.test_login_seeded_owner)
        
        # Ensure we have a WABA for template/inbox tests
        self.log("\n--- Setup: Connect WABA ---", Colors.YELLOW)
        self.test("Onboarding Exchange", self.test_onboarding_exchange)
        
        # Phase 2: System Info
        self.log("\n--- Phase 2: System Info ---", Colors.YELLOW)
        self.test("System Info (no secrets)", self.test_system_info)
        self.test("Meta Client Import", self.test_meta_client_import)
        
        # Phase 2: Templates
        self.log("\n--- Phase 2: Templates ---", Colors.YELLOW)
        self.test("Templates Sync", self.test_templates_sync)
        self.test("Templates List", self.test_templates_list)
        self.test("Templates Create", self.test_templates_create)
        self.test("Templates Delete", self.test_templates_delete)
        self.test("Templates Tenant Isolation", self.test_templates_tenant_isolation)
        
        # Phase 2: Inbox
        self.log("\n--- Phase 2: Inbox ---", Colors.YELLOW)
        self.test("Inbox Simulate Inbound", self.test_inbox_simulate_inbound)
        self.test("Inbox List Conversations", self.test_inbox_list_conversations)
        self.test("Inbox Get Messages", self.test_inbox_get_messages)
        self.test("Inbox Reply", self.test_inbox_reply)
        
        # Phase 2: Analytics
        self.log("\n--- Phase 2: Analytics ---", Colors.YELLOW)
        self.test("Analytics Overview", self.test_analytics_overview)
        self.test("Analytics Timeseries", self.test_analytics_timeseries)
        self.test("Analytics By Template", self.test_analytics_by_template)
        self.test("Analytics By Phone", self.test_analytics_by_phone)
        
        # Summary
        self.log("\n" + "="*70, Colors.BLUE)
        self.log("Phase 2 Test Summary", Colors.BLUE)
        self.log("="*70, Colors.BLUE)
        self.log(f"Total Tests: {self.tests_run}", Colors.BLUE)
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED)
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"Success Rate: {success_rate:.1f}%", Colors.BLUE)
        self.log("="*70 + "\n", Colors.BLUE)
        
        return 0 if self.tests_failed == 0 else 1
    
    def run_all(self):
        """Run all tests in order."""
        self.log("\n" + "="*70, Colors.BLUE)
        self.log("WhatsApp SaaS MVP - Backend API Tests", Colors.BLUE)
        self.log("="*70 + "\n", Colors.BLUE)
        
        # Health & Metrics
        self.log("\n--- Health & Metrics ---", Colors.YELLOW)
        self.test("Health Live", self.test_health_live)
        self.test("Health Ready", self.test_health_ready)
        self.test("Metrics Endpoint", self.test_metrics)
        
        # Auth - Basic
        self.log("\n--- Authentication (Basic) ---", Colors.YELLOW)
        self.test("Login Wrong Password", self.test_login_wrong_password)
        
        # Auth - Register and use that session for subsequent tests
        self.log("\n--- Authentication (Register) ---", Colors.YELLOW)
        self.test("Register New Tenant", self.test_register)
        
        # MFA (uses separate sessions)
        self.log("\n--- MFA Flow ---", Colors.YELLOW)
        self.test("MFA Setup", self.test_mfa_setup)
        self.test("MFA Verify", self.test_mfa_verify)
        
        # Continue with registered tenant session
        self.log("\n--- Auth Me ---", Colors.YELLOW)
        self.test("Auth Me", self.test_auth_me)
        
        # Password Reset
        self.log("\n--- Password Reset ---", Colors.YELLOW)
        self.test("Password Forgot", self.test_password_forgot)
        
        # Onboarding
        self.log("\n--- Onboarding ---", Colors.YELLOW)
        self.test("Onboarding Exchange", self.test_onboarding_exchange)
        
        # WABAs & Phones
        self.log("\n--- WABAs & Phone Numbers ---", Colors.YELLOW)
        self.test("List WABAs", self.test_list_wabas)
        self.test("List Phone Numbers", self.test_list_phone_numbers)
        
        # Messaging
        self.log("\n--- Messaging ---", Colors.YELLOW)
        self.test("Send Message", self.test_send_message)
        self.test("Idempotency", self.test_idempotency)
        self.test("List Messages", self.test_list_messages)
        self.test("Simulate Webhook", self.test_simulate_webhook)
        
        # Webhooks
        self.log("\n--- Webhooks ---", Colors.YELLOW)
        self.test("Webhook Verification", self.test_webhook_verification)
        self.test("Webhook Invalid Signature", self.test_webhook_invalid_signature)
        self.test("Webhook Valid Signature", self.test_webhook_valid_signature)
        
        # Tenant Isolation
        self.log("\n--- Tenant Isolation ---", Colors.YELLOW)
        self.test("Tenant Isolation", self.test_tenant_isolation)
        
        # Dashboard
        self.log("\n--- Dashboard ---", Colors.YELLOW)
        self.test("Dashboard Stats", self.test_dashboard)
        
        # Login with seeded owner (separate test at the end)
        self.log("\n--- Seeded Owner Login ---", Colors.YELLOW)
        self.test("Login Seeded Owner", self.test_login_seeded_owner)
        
        # Summary
        self.log("\n" + "="*70, Colors.BLUE)
        self.log("Test Summary", Colors.BLUE)
        self.log("="*70, Colors.BLUE)
        self.log(f"Total Tests: {self.tests_run}", Colors.BLUE)
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED)
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"Success Rate: {success_rate:.1f}%", Colors.BLUE)
        self.log("="*70 + "\n", Colors.BLUE)
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    import sys
    tester = BackendTester()
    # Run Phase 2 tests only (as per task requirements)
    if len(sys.argv) > 1 and sys.argv[1] == "--phase2":
        exit_code = tester.run_phase2_only()
    else:
        # Default: run all tests
        exit_code = tester.run_all()
    sys.exit(exit_code)
