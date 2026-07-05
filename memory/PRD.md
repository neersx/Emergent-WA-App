# WhatsApp Business Management Platform — PRD

## Problem Statement
Multi-tenant WhatsApp Business Management Platform (WABA Console) built on FARM stack.
Phase 1 MVP completed. Switched from mock mode to live mode with real Meta API credentials.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui (port 3000)
- **Backend**: FastAPI + Motor/MongoDB (port 8001)
- **Database**: MongoDB (local)
- **Auth**: JWT with refresh tokens, bcrypt, MFA (TOTP), Fernet-encrypted credential storage

## Key Environment Variables (backend/.env)
- MONGO_URL, DB_NAME, JWT_SIGNING_KEY, TOKEN_ENCRYPTION_KEY
- META_APP_ID=1506794823304106
- META_APP_SECRET=84407ce0f0ea60ccba2217830ce32eab
- META_EMBEDDED_SIGNUP_CONFIG_ID=1823455155290835
- META_WEBHOOK_VERIFY_TOKEN=DW-WhatsApp-Verify-7f2d9a71-8d6b-4d35-a87c-2c5d90d67b11
- META_GRAPH_API_VERSION=v21.0
- META_MOCK_MODE=false  ← LIVE MODE

## What's Been Implemented (Phase 1)

### Backend
- Multi-tenant auth (register, login, logout, JWT refresh, MFA TOTP, password reset)
- Meta Embedded Signup onboarding (live + mock modes)
- Webhook ingestion with HMAC-SHA256 signature verification
- Template management (list from Meta or mock)
- Template send + text send via Meta Graph API
- Inbox (inbound message threading)
- Analytics (message stats)
- Admin routes (WABAs, phone numbers, dashboard, audit)
- Background worker with MongoDB-backed queue
- Prometheus metrics + health endpoint
- Seed data (super admin + demo tenant)

### Frontend
- Marketing pages (Home, Features, Pricing, Contact)
- Auth pages (Login, Register, Forgot/Reset Password)
- Admin pages: Dashboard, Connect WhatsApp, WABAs & Numbers, Templates, Send, Message Log, Inbox, Analytics, Security (MFA), Settings
- Live/Mock mode indicator in AppShell (dynamic, fetched from /api/system/info)

## Live Mode Status (Updated 2026-07-05)
- META_MOCK_MODE=false → all Meta Graph API calls are real
- AppShell now shows "LIVE MODE" (green) / "MOCK MODE" (amber) badge dynamically
- Webhook URL: https://5a10e0c5-b4e7-44a4-a0d5-4f1914ff7455.preview.emergentagent.com/api/webhooks/meta
- Webhook verify token: DW-WhatsApp-Verify-7f2d9a71-8d6b-4d35-a87c-2c5d90d67b11

## Backlog / Phase 2
- P0: End-to-end E2E test with real Meta sandbox
- P1: Tenant management UI (invite users, manage seats)
- P1: Template creation / approval flow
- P2: Bulk send campaigns
- P2: Stripe billing integration
- P2: Multi-language support
