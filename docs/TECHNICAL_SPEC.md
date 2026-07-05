# WhatsApp Business Management Platform
## Technical & Functional Specification

> **Phase 1–2.5 Complete** · FARM Stack · Meta Graph API v21.0 · July 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Tech Stack](#2-tech-stack)
3. [System Architecture](#3-system-architecture)
4. [Multi-Tenancy & RBAC](#4-multi-tenancy--rbac)
5. [Security Architecture](#5-security-architecture)
6. [Data Model](#6-data-model)
7. [MongoDB Collections](#7-mongodb-collections)
8. [Functional Flows](#8-functional-flows)
9. [API Reference](#9-api-reference)
10. [WebSocket Protocol](#10-websocket-protocol)
11. [Infrastructure & Config](#11-infrastructure--config)
12. [Phase Roadmap](#12-phase-roadmap)

---

## 1. Executive Summary

A **multi-tenant SaaS platform** that enables Technology Providers to:

- Onboard client businesses onto WhatsApp via **Meta Embedded Signup**
- Manage **message templates** (create, submit to Meta, track approval status)
- Send **outbound template messages** to customers at scale
- Receive and reply to **inbound messages** in a real-time conversation inbox
- Track **per-message costs** with daily rollup billing reports
- View **platform-wide analytics** with cross-tenant oversight

| Metric | Value |
|--------|-------|
| Backend modules | 22 |
| Frontend pages | 15 |
| MongoDB collections | 17 |
| REST endpoints | 40+ |
| Messages in demo | 576 |
| Daily cost rollup rows | 266 |

---

## 2. Tech Stack

### Frontend

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Framework | **React** | 19.0 | SPA, hooks, context |
| Routing | **React Router DOM** | 7.15 | Client-side routing, protected routes |
| Styling | **Tailwind CSS** | 3.4 | Utility-first, design tokens |
| Components | **shadcn/ui + Radix UI** | — | Accessible headless components |
| Icons | **Lucide React** | 0.516 | SVG icon set |
| Charts | **Recharts** | 3.6 | Line, Bar, Pie charts |
| HTTP Client | **Axios** | 1.16 | REST calls, token refresh interceptor |
| Real-time | **WebSocket API** (native) | — | Live inbox & template status push |
| Forms | **React Hook Form + Zod** | 7.56/3.24 | Form state & validation |
| Animations | **Framer Motion** | 11.18 | Micro-animations |
| Build | **CRACO + Webpack** | 7.1 | Path aliases (`@/`), CRA override |

### Backend

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Framework | **FastAPI** | 0.110 | Async REST + WebSocket, OpenAPI |
| ASGI Server | **Uvicorn** | 0.25 | ASGI server with hot-reload |
| Validation | **Pydantic v2** | 2.13 | Request/response models |
| DB Driver | **Motor** (async MongoDB) | 3.3 | All MongoDB I/O |
| Auth | **PyJWT + bcrypt + pyotp** | — | JWT, password hash, TOTP MFA |
| Encryption | **cryptography (Fernet)** | 49.0 | Business token encryption at rest |
| HTTP Client | **httpx** | 0.28 | Meta Graph API calls (async + retry) |
| Logging | **loguru** | 0.7 | Structured logging with trace-id |
| Metrics | **prometheus_client** | 0.20 | Prometheus metrics endpoint |
| Excel | **openpyxl** | 3.1 | XLSX export generation |
| Phone | **phonenumbers** | 9.0 | WA ID → country code |

### Database & Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| Database | **MongoDB** | 17 collections, compound indexes, TTL |
| Job Queue | **MongoDB-backed** (custom) | `mq_jobs` — atomic claim, visibility timeout, 5× retry |
| Process Manager | **Supervisor** | Frontend (3000), Backend (8001), MongoDB |
| Reverse Proxy | **Nginx** | `/api/*` → 8001, else → 3000; WS upgrade |
| Media | **Local disk** (→ S3 configurable) | HMAC-signed time-limited URLs |
| External API | **Meta Graph API v21.0** | Templates, messages, media, webhooks |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│  ┌──────────────────┐  ┌────────────┐  ┌──────────────────┐    │
│  │  React 19 SPA    │  │ FB JS SDK  │  │ WebSocket Client │    │
│  │  (15 pages)      │  │ Embed Sign │  │ wss://host/api/  │    │
│  └────────┬─────────┘  └─────┬──────┘  └────────┬─────────┘    │
└───────────┼─────────────────┼──────────────────┼───────────────┘
            │ axios            │ auth code        │ wss://
            ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                           │
│              /api/* → :8001  |  /* → :3000                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                   FastAPI Application (:8001)                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ REST Routers │  │   WebSocket  │  │  Background Worker   │  │
│  │ auth         │  │ /api/ws/inbox│  │  asyncio task        │  │
│  │ onboarding   │  │ cookie auth  │  │  poll 500ms          │  │
│  │ templates    │  │ tenant-scoped│  │  process_webhook     │  │
│  │ messaging    │  │ broadcast    │  │  sync_templates_waba │  │
│  │ inbox        │  └──────────────┘  └──────────────────────┘  │
│  │ analytics    │                                                │
│  │ platform     │  ┌──────────────┐  ┌──────────────────────┐  │
│  │ webhooks     │  │ Meta Graph   │  │   Media Storage      │  │
│  └──────────────┘  │ Client       │  │   /app/media/        │  │
│                    │ httpx+retry  │  │   HMAC signed URLs   │  │
│                    └──────┬───────┘  └──────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                ┌───────────┼───────────────┐
                ▼           ▼               ▼
         ┌──────────┐  ┌─────────┐  ┌────────────────┐
         │ MongoDB  │  │  Meta   │  │  Meta Cloud API│
         │ 17 colls │  │ Graph   │  │  (Webhooks →)  │
         └──────────┘  │ API v21 │  └────────────────┘
                       └─────────┘
```

---

## 4. Multi-Tenancy & RBAC

Every MongoDB query includes `{"tenant_id": p.tenant_id}` from the `Principal` object — enforced at the dependency level via `require_tenant()`.

### Role Hierarchy

| Role | Scope | MFA |
|------|-------|-----|
| `PlatformSuperAdmin` | All tenants (audited) | Required |
| `TenantOwner` | Own tenant | Optional |
| `TenantAdmin` | Own tenant | Optional |
| `Agent` | Own tenant (inbox only) | Optional |
| `Viewer` | Own tenant (read-only) | Optional |

### Elevated Access Pattern (PlatformSuperAdmin)

```python
# platform.py — every cross-tenant read calls this first
async def _audited(action: str, actor_id: str, detail: dict):
    await db.audit_log.insert_one({
        "actor_user_id": actor_id,
        "action": f"platform.elevated.{action}",
        "metadata": detail,
        "created_at": now(),
        "tenant_id": None,  # cross-tenant flag
    })
```

---

## 5. Security Architecture

### Authentication
- **Passwords**: bcrypt rounds=10, never stored plaintext
- **Access tokens**: JWT HS256, 15-minute TTL, carries `sub`, `role`, `tenant_id`, `mfa_complete`
- **Refresh tokens**: 48-byte random opaque string, SHA-256 hash stored in MongoDB, 14-day TTL, httpOnly Secure SameSite=None cookie, rotated on every refresh
- **MFA**: TOTP via pyotp, secret Fernet-encrypted at rest, required for PlatformSuperAdmin
- **WebSocket auth**: httpOnly cookie automatically sent in WS handshake headers, read via FastAPI `Cookie()` dependency

### Credential Storage
- **Meta business tokens**: Fernet (AES-128-CBC + HMAC-SHA256) encrypted before MongoDB insert
- **Webhook verification**: HMAC-SHA256 of raw request body validated before any processing
- **Media URLs**: HMAC-SHA256 signed with 1-hour TTL, never publicly accessible

---

## 6. Data Model

### Core Entities

```
tenants ──< wabas ──< phone_numbers ──< messages >── conversations
   │           └──< waba_credentials       │
   └──< users                              └──< media_assets
   └──< usage_daily_rollup
   └──< template_perf_rollup
```

### Key Document Shapes

**Message** (the central document):
```json
{
  "_id": "uuid",
  "tenant_id": "...",
  "phone_number_id": "...",
  "conversation_id": "...",
  "direction": "outbound|inbound",
  "msg_type": "text|template|image|video|audio|document|location|contacts|interactive|reaction",
  "status": "queued|sent|delivered|read|failed",
  "meta_message_id": "wamid.xxx",
  "template_name": "order_shipped",
  "body": "...",
  "media_id": "...",
  "mime_type": "image/jpeg",
  "latitude": null,
  "pricing_category": "utility",
  "pricing_billable": true,
  "cost_amount": 0.015,
  "country_code": "IN",
  "month": "2026-07",
  "created_at": "2026-07-05T10:00:00Z"
}
```

**Usage Daily Rollup** (billing aggregate):
```json
{
  "_id": "tenant_id:2026-07-05:marketing:US",
  "tenant_id": "...",
  "day": "2026-07-05",
  "category": "marketing",
  "country_code": "US",
  "delivered_count": 45,
  "billable_count": 45,
  "free_count": 0,
  "cost_amount": 1.1250,
  "cost_currency": "USD"
}
```

---

## 7. MongoDB Collections

| Collection | Docs | Purpose | Key Indexes |
|-----------|------|---------|-------------|
| `users` | 3 | Platform users | unique(email), by_tenant |
| `tenants` | 2 | Tenant records | by_name |
| `refresh_tokens` | 35 | Opaque refresh token hashes | unique(token_hash), TTL(expires_at) |
| `wabas` | 3 | WhatsApp Business Accounts | unique(waba_id), by_tenant |
| `waba_credentials` | 3 | Fernet-encrypted Meta tokens | unique(waba_id) |
| `phone_numbers` | 5 | Phone numbers per WABA | unique(phone_number_id) |
| `templates` | 16 | Message templates + components | unique(tenant+waba+name+lang) |
| `messages` | 576 | All messages (in+out) | by_tenant_time, by_conv_time, by_meta_id |
| `conversations` | 15 | Conversation threads | by_phone_contact |
| `usage_daily_rollup` | 266 | Cost rollup by day/category/country | by_tenant_day |
| `template_perf_rollup` | 36 | Template stats by month | by_tenant_month |
| `media_assets` | 0 | Downloaded media metadata | unique(tenant+meta_media_id) |
| `webhook_events_raw` | 6 | Raw webhook payloads | by_time |
| `mq_jobs` | 6 | Job queue (process/sync) | by_status |
| `audit_log` | 7 | Immutable action trail | by_tenant_time |
| `idempotency_keys` | 0 | Dedup outbound sends | unique(tenant+key), TTL 24h |
| `rate_limits` | — | Per-phone rate bucket | by_phone+window |

---

## 8. Functional Flows

### 8.1 Webhook Processing (Critical Path)

```
Meta Cloud  ──POST──►  /api/webhooks/meta
                         │
                         ├─ verify HMAC-SHA256 signature
                         ├─ insert webhook_events_raw
                         ├─ enqueue("process_webhook", {event_id})
                         └─ 200 ACK  ◄── MUST be < 1 second
                                              │
                         Worker (async)       │
                              ◄───────────────┘
                              │
                              ├─ parse statuses[] → update messages
                              ├─ parse messages[] → upsert conversations
                              ├─ create inbound message document
                              ├─ download media (if any) → media_assets
                              ├─ update usage_daily_rollup (cost)
                              └─ broadcast to WebSocket clients
```

### 8.2 Cost Calculation Logic

```python
def is_billable(category, billable_from_webhook, service_window_open, free_entry_point):
    if free_entry_point:               return False   # 72h free window
    if billable_from_webhook is not None: return billable_from_webhook  # trust Meta
    if category == "marketing":        return True    # always billable
    if category == "authentication":   return True    # always billable
    if category == "utility":          return not service_window_open  # free in window
    return not service_window_open     # service/free-form: free in window
```

### 8.3 Service Window Rules

| Scenario | Window Type | Duration | Free? |
|----------|-------------|----------|-------|
| Customer sends a message | Service window | 24 hours | Yes |
| Click-to-WA / Ad referral | Free Entry Point | 72 hours | Yes |
| Business sends template | Depends on category | — | Per CBP |
| Window expired → template only | None | — | Billable |

### 8.4 Template Approval Lifecycle

```
Create (POST /api/templates)
  │
  ├─ Live mode: POST /{waba_id}/message_templates → Meta
  │   └─ Meta returns {id, status: "PENDING"}
  │
  ├─ Webhook: message_template_status_update
  │   └─ Worker updates template.status → APPROVED/REJECTED/PAUSED
  │
  └─ Periodic sync: worker pulls all templates from Meta every 10 min
```

---

## 9. API Reference

See full table in `technical-architecture.html` (40+ endpoints).

Key groupings:
- `/api/auth/*` — Register, login, MFA, password reset, refresh, logout
- `/api/onboarding/*` — Embedded Signup exchange
- `/api/templates/*` — CRUD + Meta Graph submit + sync
- `/api/messages/*` — Send template, list, simulate webhook
- `/api/inbox/*` — Conversations, thread, reply, assign, close, media
- `/api/analytics/*` — Overview, timeseries, dashboard, cost, export
- `/api/platform/*` — Cross-tenant (PlatformSuperAdmin, audited)
- `/api/webhooks/meta` — Meta GET challenge + POST ingestion
- `/api/ws/inbox` — WebSocket endpoint

---

## 10. WebSocket Protocol

**URL**: `wss://<host>/api/ws/inbox`

**Auth**: httpOnly `access_token` cookie (auto-sent by browser in WS handshake)

### Event Types (Server → Client)

| Type | Payload | Trigger |
|------|---------|---------|
| `auth_ok` | `{tenant_id}` | Connection authenticated |
| `new_message` | `{conversation_id, message}` | Inbound message received |
| `status_update` | `{message_id, status}` | Delivery/read status changed |
| `template_update` | `{template_name, status, reason}` | Template approved/rejected by Meta |
| `ping` | — | Keepalive (client replies "ping") |

---

## 11. Infrastructure & Config

### Process Management (Supervisor)

| Process | Command | Port |
|---------|---------|------|
| `frontend` | `yarn start` | 3000 |
| `backend` | `uvicorn server:app --reload` | 8001 |
| `mongodb` | `mongod --bind_ip_all` | 27017 |
| `nginx-code-proxy` | `nginx` | 80/443 |

### Key Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_URL` | ✅ | MongoDB connection string |
| `JWT_SIGNING_KEY` | ✅ | 64-char hex for JWT HS256 |
| `TOKEN_ENCRYPTION_KEY` | ✅ | Fernet key for token encryption |
| `META_APP_ID` | Live mode | Meta App ID |
| `META_APP_SECRET` | Live mode | Meta App Secret |
| `META_EMBEDDED_SIGNUP_CONFIG_ID` | Live mode | Embedded Signup config |
| `META_WEBHOOK_VERIFY_TOKEN` | Live mode | Webhook challenge token |
| `META_MOCK_MODE` | Optional | `false` = live, `true` = stub |
| `MEDIA_STORAGE_MODE` | Optional | `disk` (default) or `s3` |
| `REACT_APP_BACKEND_URL` | ✅ | Frontend API base URL |

---

## 12. Phase Roadmap

### ✅ Phase 1 (Complete)
Multi-tenant auth · MFA · JWT + refresh · Embedded Signup · Webhook ingestion (< 1s ACK) · Outbound template send · Rate limiting · Idempotency · Marketing pages

### ✅ Phase 2 (Complete)
Template component builder UI · Meta Graph submit · Status tracking (PENDING→APPROVED→REJECTED) · Real-time inbox (WebSocket) · 10+ message types · Media download + storage · 24h + 72h window enforcement · Cost capture (CBP model) · Daily rollup

### ✅ Phase 2.5 (Complete)
Usage & Billing dashboard · MTD spend with trend · Cost by category + country · CSV/XLSX export · Platform super-admin (audited cross-tenant) · Per-tenant drill-down + export · Analytics with date-range · Demo seed data (576 messages, 266 rollup rows)

### 🔜 Phase 3 (Planned)
- Proactive alerting (quality-rating drop, failure spikes)
- Tenant management UI (invite users, manage roles)
- Stripe billing integration (charge based on usage_daily_rollup)
- Bulk campaign broadcasting
- ClickHouse analytics warehouse
- Horizontal scaling / read replicas
- Secrets in Vault
- AI chatbot / auto-replies

---

*WhatsApp Business Management Platform · FARM Stack · Phase 1–2.5 · July 2026*
