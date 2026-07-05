# plan.md (Updated)

## 1) Objectives
- Confirm Phase 1 MVP is **complete on the Emergent FARM stack** (FastAPI + React + MongoDB) with **mock Meta mode**.
- Deliver a fully working, demoable system covering the full workflow end-to-end:
  - Connect WhatsApp (mock Embedded Signup) → send template (idempotent) → webhook verify+enqueue (**ACK <1s**, observed ~50ms) → async worker projection → message status updates.
- Maintain key non-functional requirements:
  - **Tenant isolation** (server-enforced), **RBAC**, **TOTP MFA**, encrypted-at-rest business tokens, audit logging, health/metrics.
- Provide tested deliverables with documented credentials and repeatable demo/test flows.

## 2) Implementation Steps

### Phase 1 — Core Flow POC (Isolation) (do not proceed until green)
**Goal:** Validate the failure-prone pipeline (signature verify + fast ACK + queue + worker projection + idempotency) before full UI.

**Status: ✅ Completed**
- Implemented POC-capable modules (carried forward into full build):
  - HMAC signature verification on raw bytes
  - Webhook raw persistence + durable job enqueue
  - MongoDB-backed queue with atomic claim (`find_one_and_update`) and visibility timeout
  - Async worker loop that projects webhook events into message status updates
  - Idempotency key enforcement via unique constraint
- Validation:
  - `backend/tests/test_core.py` covers core stories:
    - mock onboarding → send template twice w/ same idempotency key → webhook good/bad signature → worker projections
  - Observed webhook ACK time well under 1s (≈50ms typical).

**User stories (Phase 1)**
1. As a developer, I can create a mock WABA+phone via an API call so I can test messaging quickly. ✅
2. As a developer, I can send a template message and see it recorded (queued/sent). ✅
3. As a developer, sending the same request with the same idempotency key only creates one message. ✅
4. As a system, the webhook endpoint rejects invalid signatures. ✅
5. As a system, a valid webhook is ACKed quickly and processed asynchronously by the worker. ✅

---

### Phase 2 — V1 App Development (MVP UI + full API)
**Goal:** Deliver the full Phase 1 MVP product surface: marketing site + admin portal + complete backend.

**Status: ✅ Completed**

**Backend (FastAPI modular monolith)**
1. Implemented modules (located under `/app/backend/app/`):
   - `config.py`, `db.py`, `models.py`, `tenancy.py`, `auth.py`, `crypto_utils.py`, `meta_client.py` (mock)
   - `onboarding.py`, `messaging.py`, `webhooks.py`, `queue.py`, `worker.py`
   - `admin_routes.py`, `auth_routes.py`, `health.py`, `seed.py`
   - App entry: `/app/backend/server.py`
2. Auth:
   - Email+password, bcrypt hashing ✅
   - JWT access (~15m) + rotating refresh tokens in httpOnly cookies ✅
   - Password reset flow (reset token logged to backend console) ✅
   - TOTP MFA (required for super-admin; optional for others) ✅
   - RBAC roles present (PlatformSuperAdmin, TenantOwner, TenantAdmin, Agent, Viewer) ✅
3. Multi-tenancy:
   - `tenant_id` embedded in JWT; dependencies enforce tenant context ✅
   - All tenant-owned collections filtered by `tenant_id` ✅
4. Onboarding:
   - `POST /api/onboarding/exchange` (mock) persists WABA + phone + **encrypted** business token ✅
   - `GET /api/wabas`, `GET /api/phone-numbers` ✅
5. Messaging:
   - `POST /api/messages/send` with idempotency + per-phone rate limit ✅
   - `GET /api/messages` message log ✅
   - `POST /api/messages/{id}/simulate-webhook` demo helper (delivered/read/failed) ✅
6. Webhooks/worker:
   - `GET /api/webhooks/meta` verify challenge ✅
   - `POST /api/webhooks/meta` verify signature → raw store → enqueue → fast ACK ✅
   - Worker projects events into `messages` and `conversations` ✅
7. Observability + ops:
   - Structured logs with trace IDs ✅
   - `/health/live`, `/health/ready`, `/metrics` ✅
   - Audit log for key actions ✅
8. Seed data on startup:
   - `super@admin.com / SuperAdmin123!` (MFA required) ✅
   - `owner@demo.com / Owner123!` ✅
   - **Fix applied:** demo account is **auto-reset** on every startup to avoid MFA poisoning across test runs ✅

**Frontend (React SPA)**
1. Public marketing routes:
   - `/`, `/pricing`, `/features`, `/contact` ✅
2. Auth routes:
   - `/login`, `/register`, `/forgot-password`, `/reset-password` ✅
3. Protected admin routes:
   - `/app/dashboard`, `/app/connect`, `/app/wabas`, `/app/send`, `/app/messages`, `/app/security` ✅
4. Core UI flows:
   - Register → creates tenant+owner → dashboard ✅
   - Connect WhatsApp → launch mock embedded signup → exchange → WABA/phone appears ✅
   - Send template → queued/sent; simulate webhook → delivered/read ✅
   - Message log + status badges + auto-refresh ✅
5. API client:
   - axios with credentials + refresh retry on 401 ✅
   - AuthContext + ProtectedRoute ✅
6. UX fix:
   - **Mock Mode badge always visible** in admin shell ✅

**End of Phase 2:** Completed `testing_agent_v3` full run; applied fixes; re-tested to clean pass.

**User stories (Phase 2)**
1. As a visitor, I can browse marketing pages and click Get Started. ✅
2. As a new user, I can register and immediately land on my tenant dashboard. ✅
3. As a returning user, I can log in and complete MFA if enabled. ✅
4. As a tenant owner, I can connect WhatsApp via a mock embedded signup and see WABAs/phones listed. ✅
5. As a tenant owner, I can send a template message and see it appear in the message log. ✅

---

### Phase 3 — Hardening + Coverage (tests + security + tenant isolation proof)
**Goal:** Formalize coverage, prove correctness properties, and close test gaps.

**Status: ✅ Completed (via POC tests + testing_agent_v3)**
1. Backend verification:
   - POC test script (`backend/tests/test_core.py`) validates:
     - tenant isolation, webhook signature good/bad, idempotency, worker projection, MFA ✅
   - `testing_agent_v3` results: **backend 22/22 pass (100%)** ✅
2. Frontend verification:
   - `testing_agent_v3` results: **frontend 7/7 pass** after fixes ✅
3. Security/ops checks:
   - Tokens not returned to FE; business tokens encrypted at rest ✅
   - Cross-tenant access blocked (404) ✅
   - Webhook invalid signatures rejected with 401 and no persistence ✅
   - Health/metrics endpoints validated ✅

**User stories (Phase 3)**
1. As a tenant owner, I can’t access other tenants’ WABAs or messages even if I guess IDs. ✅
2. As an admin, I can verify health/metrics endpoints respond. ✅
3. As a user, I see clear errors when actions fail (invalid MFA code, invalid reset token, etc.). ✅
4. As a tenant owner, sending duplicate requests doesn’t duplicate messages. ✅
5. As an operator, I can see webhook processing succeed/fail in logs and raw event storage. ✅

---

### Phase 4 — Polish + Delivery
**Goal:** Documentation, demo readiness, and final delivery artifacts.

**Status: ✅ Completed**
1. UI polish delivered:
   - Marketing site, branded auth screens, admin shell layout, toasts, empty states ✅
2. Documentation + operational notes:
   - Seed credentials recorded in `/app/memory/test_credentials.md` ✅
   - Demo state stability ensured via demo account auto-reset ✅
3. Final test verification:
   - testing_agent_v3 backend 100% pass; frontend 100% pass after fixes ✅

**User stories (Phase 4)**
1. As a demo user, I can complete the full flow in under 2 minutes without confusion. ✅
2. As a user, I can enroll/disable MFA from Security settings. ✅
3. As a super-admin, I’m forced to enroll MFA on first login. ✅
4. As a tenant owner, I can view the message log and simulate status progression reliably. ✅
5. As an operator, I can confirm readiness/liveness/metrics endpoints for deployment. ✅

## 3) Next Actions
**Current state: Phase 1 MVP COMPLETE.**

If continuing to Phase 2+ roadmap (optional):
1. Add template management UI + sync (list templates, status, languages).
2. Add conversation inbox (threads, inbound/outbound messaging UI, service window tracking).
3. Add real Meta integration toggle (turn off mock mode) and secrets management.
4. Add usage analytics + billing scaffolding.
5. Add stronger test harness (Playwright suite) and CI pipeline.

## 4) Success Criteria
- Core pipeline proven: **idempotent send**, **signature-verified webhook**, **<1s ACK**, **async worker projection**, **status updates** ✅
- V1 UI covers US1–US16 (mock-mode) with good error/empty/loading states ✅
- Tenant isolation verified by tests ✅
- Health/metrics endpoints respond ✅
- Seed accounts work and super-admin MFA is enforced ✅
- `testing_agent_v3` results:
  - Backend: **22/22 pass (100%)** ✅
  - Frontend: **7/7 pass after fixes** ✅
