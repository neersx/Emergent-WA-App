# WhatsApp Business Management Platform — PRD

## Problem Statement
Multi-tenant WhatsApp Business Management Platform (WABA Console) built on FARM stack.
Phase 1 (auth, webhooks, mock mode), Phase 2 (template builder, real-time inbox, cost tracking),
Phase 2.5 (billing dashboard, platform admin, exports, core dashboard).
Now running in LIVE MODE with real Meta API credentials.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui (port 3000)
- **Backend**: FastAPI + Motor/MongoDB (port 8001)
- **Database**: MongoDB (local)
- **Auth**: JWT with refresh tokens, bcrypt, MFA (TOTP), Fernet-encrypted credential storage

## Live Mode Config (/app/backend/.env)
- META_APP_ID=1506794823304106
- META_APP_SECRET=84407ce0f0ea60ccba2217830ce32eab
- META_EMBEDDED_SIGNUP_CONFIG_ID=1823455155290835
- META_WEBHOOK_VERIFY_TOKEN=DW-WhatsApp-Verify-7f2d9a71-8d6b-4d35-a87c-2c5d90d67b11
- META_GRAPH_API_VERSION=v21.0
- META_MOCK_MODE=false ← LIVE MODE
- MEDIA_STORAGE_MODE=disk / MEDIA_STORAGE_PATH=/app/media
- SIGNALR_ENABLED=true

## Webhook URL (configure in Meta App Dashboard)
https://5a10e0c5-b4e7-44a4-a0d5-4f1914ff7455.preview.emergentagent.com/api/webhooks/meta
Verify token: DW-WhatsApp-Verify-7f2d9a71-8d6b-4d35-a87c-2c5d90d67b11

## What's Implemented

### Phase 1 (Complete)
- Multi-tenant auth (register, login, JWT refresh, MFA TOTP, password reset)
- Meta Embedded Signup onboarding (live + mock)
- Webhook ingestion with HMAC-SHA256 signature verification
- Background worker (MongoDB-backed queue)
- Seed data (super admin + demo tenant + demo WABA/phone)
- Marketing pages, auth pages

### Phase 2 (Complete)
- **Template Management**: Full CRUD against Meta Graph API, component builder (header/body/footer/buttons), live WhatsApp preview, status tracking (PENDING/APPROVED/REJECTED/PAUSED/DISABLED), rejection reason display, sync from Meta, periodic background sync
- **Real-time Inbox**: WebSocket at /api/ws/inbox (cookie auth), all 10+ message types rendered (text/image/video/audio/document/location/contacts/interactive/reaction/sticker), agent assignment, close/reopen conversation, 24h + 72h free-entry window enforcement
- **Cost capture**: Billability logic (marketing=always, utility=free-in-window, auth=always, service=free-in-window), daily rollup in usage_daily_rollup collection
- **Media**: Download from Meta, store at /app/media/{tenant_id}/, serve via signed URLs
- **Worker**: Extended for all message types, cost capture, WS broadcast, periodic template sync

### Phase 2.5 (Complete)
- **Usage & Billing page** (/app/usage): MTD spend with trend vs last month, cost by category pie, cost by country bar, daily rollup table, CSV + XLSX export
- **Platform super-admin** (/app/platform): Cross-tenant overview (total tenants/messages/cost), per-tenant drill-down with audited elevated queries, export per tenant
- **Analytics extended**: Dashboard endpoint (delivery/read/failure rates + failure reasons + cost burn + throughput), date-range filters (from_date/to_date) on all endpoints, template performance table
- **Exports**: GET /api/analytics/export?format=csv|xlsx, GET /api/platform/tenants/{id}/export
- **Data model**: media_assets collection, template_perf_rollup collection, month field on messages, country code extraction from WA IDs

## Collections
- users, tenants, refresh_tokens, password_resets
- wabas, waba_credentials, phone_numbers
- messages, conversations, inbox (thread)
- templates, template_perf_rollup
- usage_daily_rollup
- media_assets
- webhook_events_raw, mq_jobs
- audit_log, idempotency_keys, rate_limits

## Phase 3 (OUT OF SCOPE - placeholders only)
- Advanced analytics (ClickHouse)
- Proactive alerting (quality-rating drop, failure spikes)
- Horizontal scaling & read replicas
- Secrets in Vault
- Multi-Partner Solution / Tech Partner flows
- AI chatbot / auto-replies
- Bulk campaign broadcasting

## Prioritized Backlog

### P0 (Blocking for production)
- Connect real Meta WABA via Embedded Signup (requires real Meta App with Advanced Access)
- Webhook delivery verification from Meta (register webhook URL in Meta App Dashboard)

### P1 (High value)
- Phase 3 placeholder interfaces (alerting hooks, warehouse export endpoints)
- Tenant management UI (invite users, manage roles within tenant)
- Template creation actually submits to Meta (works for real WABAs, fails for demo seed)
- MFA setup for platform super admin

### P2 (Future)
- Stripe billing integration (charge tenants based on usage_daily_rollup)
- Multi-language UI
- Bulk campaign broadcasting (Phase 3 scope)
- S3 media storage (MEDIA_STORAGE_MODE=s3 config ready)
