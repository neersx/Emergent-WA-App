# WhatsApp Business Management Platform
## Local Development Setup Guide — macOS

> This guide sets up the full application stack on your Mac:
> **FastAPI backend** · **React frontend** · **MongoDB** · **WebSocket** · **Meta API (optional)**

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Install Prerequisites](#2-install-prerequisites)
3. [Clone the Repository](#3-clone-the-repository)
4. [MongoDB Setup](#4-mongodb-setup)
5. [Backend Setup](#5-backend-setup)
6. [Frontend Setup](#6-frontend-setup)
7. [Environment Variables](#7-environment-variables)
8. [Run the Application](#8-run-the-application)
9. [Verify Everything Works](#9-verify-everything-works)
10. [Meta API — Live Mode Setup](#10-meta-api--live-mode-setup)
11. [WebSocket Verification](#11-websocket-verification)
12. [Seed Demo Data](#12-seed-demo-data)
13. [Useful Commands](#13-useful-commands)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| macOS | Monterey 12.0 | Sonoma 14.0+ |
| RAM | 8 GB | 16 GB |
| Disk | 5 GB free | 10 GB free |
| Python | 3.11 | 3.11+ |
| Node.js | 18.x | 20.x LTS |
| MongoDB | 6.0 | 7.0 |

---

## 2. Install Prerequisites

### 2.1 Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installing, add Homebrew to your PATH (Apple Silicon Macs):
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify:
```bash
brew --version
# Homebrew 4.x.x
```

---

### 2.2 Install Python 3.11

```bash
brew install python@3.11
```

Add to PATH:
```bash
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Verify:
```bash
python3.11 --version
# Python 3.11.x
```

---

### 2.3 Install Node.js 20 LTS

```bash
brew install node@20
```

Add to PATH (if not automatic):
```bash
echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Verify:
```bash
node --version   # v20.x.x
npm --version    # 10.x.x
```

---

### 2.4 Install Yarn

```bash
npm install -g yarn
```

Verify:
```bash
yarn --version   # 1.22.x
```

---

### 2.5 Install MongoDB 7.0

```bash
# Add MongoDB Homebrew tap
brew tap mongodb/brew

# Install MongoDB
brew install mongodb-community@7.0
```

Start MongoDB as a background service:
```bash
brew services start mongodb-community@7.0
```

Verify:
```bash
mongosh --eval "db.runCommand({ connectionStatus: 1 })" --quiet
# { ok: 1 }
```

> **Alternative — Docker MongoDB:**
> ```bash
> docker run -d --name mongodb -p 27017:27017 mongo:7.0
> ```

---

### 2.6 Install Git (if not already installed)

```bash
xcode-select --install
# Or:
brew install git
```

---

## 3. Clone the Repository

```bash
# Clone from GitHub
git clone https://github.com/neersx/Emergent-WA-App.git

# Move into the project directory
cd Emergent-WA-App
```

You should see this structure:
```
Emergent-WA-App/
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── analytics.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── inbox.py
│   │   ├── media.py
│   │   ├── messaging.py
│   │   ├── meta_client.py
│   │   ├── models.py
│   │   ├── onboarding.py
│   │   ├── platform.py
│   │   ├── queue.py
│   │   ├── seed.py
│   │   ├── templates.py
│   │   ├── tenancy.py
│   │   ├── webhooks.py
│   │   ├── worker.py
│   │   └── ws.py
│   ├── requirements.txt
│   ├── seed_demo_data.py
│   └── server.py
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── craco.config.js
├── docs/
├── scripts/
├── Makefile
└── README.md
```

---

## 4. MongoDB Setup

MongoDB should already be running from step 2.5. Verify:

```bash
# Check if MongoDB service is running
brew services list | grep mongodb

# Should show:
# mongodb-community  started  username ~/Library/LaunchAgents/...
```

If not started:
```bash
brew services start mongodb-community@7.0
```

Create the application database (optional — MongoDB creates it automatically on first use):
```bash
mongosh
use whatsapp_saas
exit
```

> The app uses the database name `whatsapp_saas` by default (configurable via `DB_NAME` env var).

---

## 5. Backend Setup

### 5.1 Create Python Virtual Environment

```bash
cd backend

# Create virtual environment using Python 3.11
python3.11 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Your prompt should now show (venv)
```

> **Tip:** To deactivate later: `deactivate`

---

### 5.2 Install Python Dependencies

```bash
pip install --upgrade pip

pip install -r requirements.txt
```

This installs all required packages including:
- `fastapi==0.110.1` — API framework
- `uvicorn==0.25.0` — ASGI server
- `motor==3.3.1` — Async MongoDB driver
- `pydantic==2.13.4` — Data validation
- `python-dotenv==1.2.2` — Environment variables
- `bcrypt==4.1.3` — Password hashing
- `PyJWT==2.13.0` — JWT tokens
- `pyotp==2.9.0` — TOTP MFA
- `cryptography==49.0.0` — Fernet encryption
- `httpx==0.28.1` — Async HTTP (Meta API calls)
- `loguru==0.7.2` — Structured logging
- `openpyxl==3.1.5` — Excel export
- `phonenumbers==9.0.x` — Country code extraction

> **Install time:** ~2–3 minutes depending on internet speed.

---

### 5.3 Create Backend Environment File

```bash
# Still inside /backend
```

Create the file `/backend/.env`:

```bash
cat > .env << 'EOF'
# Database
MONGO_URL=mongodb://localhost:27017
DB_NAME=whatsapp_saas

# CORS — allow local frontend
CORS_ORIGINS=http://localhost:3000

# Auth — generate secure keys below
JWT_SIGNING_KEY=REPLACE_WITH_GENERATED_KEY
TOKEN_ENCRYPTION_KEY=REPLACE_WITH_GENERATED_KEY

# Meta API — leave as mock for now (change to false for live mode)
META_APP_ID=
META_APP_SECRET=
META_EMBEDDED_SIGNUP_CONFIG_ID=
META_WEBHOOK_VERIFY_TOKEN=my-local-verify-token
META_GRAPH_API_VERSION=v21.0
META_MOCK_MODE=true

# Media storage
MEDIA_STORAGE_MODE=disk
MEDIA_STORAGE_PATH=./media

# Worker
WORKER_ENABLED=true
WORKER_POLL_INTERVAL_MS=500

# Real-time
SIGNALR_ENABLED=true
EOF
```

#### Generate Secure Keys

Run this to generate and insert real cryptographic keys:

```bash
python3.11 -c "
import secrets, base64

jwt_key = secrets.token_hex(32)
fernet_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

print('JWT_SIGNING_KEY=' + jwt_key)
print('TOKEN_ENCRYPTION_KEY=' + fernet_key)
"
```

Copy the output and update your `.env` file:

```bash
# Example output (yours will be different):
# JWT_SIGNING_KEY=a3f1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1
# TOKEN_ENCRYPTION_KEY=xY1zAbCdEfGhIjKlMnOpQrStUvWxYz01234567890ABCDE=
```

> **Security:** Never commit `.env` to Git. The `.gitignore` already excludes it.

---

## 6. Frontend Setup

### 6.1 Install Node Dependencies

```bash
# From the project root
cd frontend

yarn install
```

> **Install time:** ~1–2 minutes. Ignore warnings about peer dependencies.

---

### 6.2 Create Frontend Environment File

```bash
# Still inside /frontend
cat > .env << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
EOF
```

> **Important:** `http://` not `https://` for local development. The WebSocket will automatically use `ws://` instead of `wss://`.

---

## 7. Environment Variables

### Backend `.env` — Complete Reference

```ini
# ── Database ─────────────────────────────────────────────────────
MONGO_URL=mongodb://localhost:27017
DB_NAME=whatsapp_saas

# ── CORS ─────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000

# ── Security (REQUIRED — generate these, never reuse across envs) ─
JWT_SIGNING_KEY=<64-char hex string>
TOKEN_ENCRYPTION_KEY=<32-byte base64 Fernet key>

# ── Meta WhatsApp API ─────────────────────────────────────────────
META_APP_ID=                          # From developers.facebook.com
META_APP_SECRET=                      # From App Settings → Basic
META_EMBEDDED_SIGNUP_CONFIG_ID=       # From WhatsApp → Embedded Signup config
META_WEBHOOK_VERIFY_TOKEN=            # Any secret string you choose
META_GRAPH_API_VERSION=v21.0
META_MOCK_MODE=true                   # true = stub all Meta calls (no credentials needed)

# ── Media Storage ─────────────────────────────────────────────────
MEDIA_STORAGE_MODE=disk               # disk | s3
MEDIA_STORAGE_PATH=./media            # Local path (relative to backend/)
MEDIA_S3_ENDPOINT=                    # S3-compatible endpoint (if mode=s3)
MEDIA_S3_BUCKET=                      # S3 bucket name
MEDIA_S3_ACCESS_KEY=                  # S3 access key
MEDIA_S3_SECRET_KEY=                  # S3 secret key

# ── Background Worker ─────────────────────────────────────────────
WORKER_ENABLED=true
WORKER_POLL_INTERVAL_MS=500

# ── Real-time ─────────────────────────────────────────────────────
SIGNALR_ENABLED=true
```

### Frontend `.env`

```ini
# URL of the FastAPI backend (NO trailing slash)
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## 8. Run the Application

You need **3 terminal windows/tabs** running simultaneously.

### Option A — 3 Separate Terminals (Simplest)

**Terminal 1 — MongoDB**
```bash
# MongoDB should already be running as a service
# If not:
brew services start mongodb-community@7.0

# Or run it directly (foreground):
mongod --dbpath /opt/homebrew/var/mongodb
```

**Terminal 2 — Backend**
```bash
cd backend
source venv/bin/activate

uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
2026-07-05 10:00:00.000 | INFO | MongoDB indexes ensured
2026-07-05 10:00:00.000 | INFO | Seeded super admin: super@admin.com
2026-07-05 10:00:00.000 | INFO | Seeded demo tenant (Demo Inc) + owner: owner@demo.com
2026-07-05 10:00:00.000 | INFO | Startup complete (mock_mode=True, worker_enabled=True)
2026-07-05 10:00:00.000 | INFO | Worker started (poll=0.5s)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

**Terminal 3 — Frontend**
```bash
cd frontend
yarn start
```

Expected output:
```
Starting the development server...

Compiled successfully!

You can now view frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

---

### Option B — Makefile (Recommended)

From the project root:

```bash
# Install all dependencies
make install

# Start all services (opens 3 background processes)
make dev

# Stop all services
make stop

# View logs
make logs
```

> See [Makefile](#makefile) section below for full commands.

---

### Option C — Single Shell Script

```bash
# From the project root
chmod +x scripts/start.sh
./scripts/start.sh
```

This starts MongoDB, backend, and frontend in separate background processes and tails all logs in one terminal.

---

## 9. Verify Everything Works

### 9.1 Check All Services

```bash
# Backend health check
curl http://localhost:8001/api/health
# {"status":"ok","mongo":"connected","worker":"running"}

# System info
curl http://localhost:8001/api/system/info
# {"mock_mode":true, "meta_app_id_configured":false, ...}

# Frontend
open http://localhost:3000
# Should open the WABA Console landing page
```

### 9.2 Test Login

```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@demo.com","password":"Owner123!"}' \
  -c /tmp/cookies.txt | python3 -m json.tool
```

Expected:
```json
{
  "user": {
    "email": "owner@demo.com",
    "role": "TenantOwner",
    "tenant_name": "Demo Inc"
  },
  "mfa_required": false
}
```

### 9.3 Test Seeded Accounts

| Account | Email | Password | Role |
|---------|-------|----------|------|
| Demo tenant owner | `owner@demo.com` | `Owner123!` | TenantOwner |
| Platform super admin | `super@admin.com` | `SuperAdmin123!` | PlatformSuperAdmin (MFA required) |

### 9.4 Run a Full Flow Test

```bash
# 1. Login and save cookies
curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@demo.com","password":"Owner123!"}' \
  -c /tmp/test-cookies.txt > /dev/null

# 2. Simulate an inbound message
curl -s -X POST http://localhost:8001/api/inbox/simulate-inbound \
  -H "Content-Type: application/json" \
  -b /tmp/test-cookies.txt \
  -d '{"contact_wa_id":"14155550001","body":"Hello from local test!"}' \
  | python3 -m json.tool
# {"conversation_id":"conv_demo_phone_seed_001_14155550001","created":true}

# 3. List conversations
curl -s http://localhost:8001/api/inbox/conversations \
  -b /tmp/test-cookies.txt | python3 -m json.tool | head -20

# 4. Check analytics
curl -s "http://localhost:8001/api/analytics/overview?days=30" \
  -b /tmp/test-cookies.txt | python3 -m json.tool
```

### 9.5 Open in Browser

Navigate to: **http://localhost:3000**

- Click **Sign in** → `owner@demo.com` / `Owner123!`
- You should land on the **Dashboard**
- The sidebar should show **MOCK MODE** in amber (since `META_MOCK_MODE=true`)

---

## 10. Meta API — Live Mode Setup

> **Skip this section** if you want to run in mock mode (default). Mock mode lets you use all features without real Meta credentials.

### 10.1 Prerequisites

1. A [Meta Developer account](https://developers.facebook.com/)
2. A Meta App with **WhatsApp** product added
3. **Advanced Access** approved for:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`

### 10.2 Get Your Credentials

From [developers.facebook.com/apps](https://developers.facebook.com/apps):

| Credential | Where to find |
|-----------|---------------|
| `META_APP_ID` | App Dashboard → Settings → Basic → App ID |
| `META_APP_SECRET` | App Dashboard → Settings → Basic → App Secret |
| `META_EMBEDDED_SIGNUP_CONFIG_ID` | WhatsApp → Embedded Signup → Configuration ID |
| `META_WEBHOOK_VERIFY_TOKEN` | Choose any secret string (you'll enter this in Meta too) |

### 10.3 Configure Webhook (ngrok required for local testing)

```bash
# Install ngrok
brew install ngrok/ngrok/ngrok

# Start ngrok tunnel on port 8001
ngrok http 8001
```

ngrok will give you a public URL like: `https://abc123.ngrok.io`

Set in Meta App Dashboard:
- **Callback URL:** `https://abc123.ngrok.io/api/webhooks/meta`
- **Verify Token:** (same value as `META_WEBHOOK_VERIFY_TOKEN` in your `.env`)

### 10.4 Update Backend `.env` for Live Mode

```ini
META_APP_ID=1506794823304106
META_APP_SECRET=your_app_secret_here
META_EMBEDDED_SIGNUP_CONFIG_ID=your_config_id
META_WEBHOOK_VERIFY_TOKEN=your-chosen-verify-token
META_MOCK_MODE=false
```

Restart the backend:
```bash
# Press Ctrl+C in the backend terminal, then:
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

## 11. WebSocket Verification

The inbox uses WebSocket for real-time updates.

### Test WebSocket Connection (CLI)

```bash
# Install wscat
npm install -g wscat

# Connect to the WebSocket endpoint
# (You need a valid session cookie first — login via browser)
wscat -c ws://localhost:8001/api/ws/inbox \
  --header "Cookie: access_token=YOUR_JWT_TOKEN"
```

### What You Should See

```json
{"type": "auth_required"}
# Send: {"token": "your_jwt_token"}
{"type": "auth_ok", "tenant_id": "..."}
# Then simulate an inbound message in another terminal:
# curl -X POST http://localhost:8001/api/inbox/simulate-inbound ...
# WebSocket should immediately receive:
{"type": "new_message", "conversation_id": "...", "message": {...}}
```

### Browser Test

1. Open http://localhost:3000
2. Login → go to **Inbox**
3. Open browser DevTools → Network → WS tab
4. You should see a connection to `ws://localhost:8001/api/ws/inbox`
5. In a separate terminal, run simulate-inbound → the inbox updates in real time

---

## 12. Seed Demo Data

Populate all tables with realistic demo data (576 messages, 16 templates, etc.):

```bash
cd backend
source venv/bin/activate

python seed_demo_data.py
```

Expected output:
```
🌱 Seeding demo data for tenant fc26e509-...
  → WABAs...
  → Phone numbers...
  → Templates...
  → Messages (300+)...
     Inserted 572 messages
  → Usage daily rollup...
     Inserted/updated 266 rollup rows
  → Template performance rollup...
     Inserted 36 template perf rows
  → Audit log entries...
     Inserted 7 audit entries

✅ Demo seed complete!
   WABAs:        3
   Phones:       5
   Templates:    16
   Messages:     576
   Conversations:15
   Rollup rows:  266
```

> The seeder is **idempotent** — safe to run multiple times.

---

## 13. Useful Commands

### Backend

```bash
# Start backend (from /backend with venv active)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Start without hot-reload (production-like)
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1

# Run backend tests
cd backend && python -m pytest tests/ -v

# Access interactive API docs
open http://localhost:8001/docs          # Swagger UI
open http://localhost:8001/redoc         # ReDoc
```

### Frontend

```bash
# Start dev server
cd frontend && yarn start

# Build for production
cd frontend && yarn build

# Run frontend tests
cd frontend && yarn test
```

### MongoDB

```bash
# Start MongoDB service
brew services start mongodb-community@7.0

# Stop MongoDB service
brew services stop mongodb-community@7.0

# Open MongoDB shell
mongosh

# Connect to the app database
mongosh whatsapp_saas

# Useful MongoDB shell commands
db.messages.count()
db.users.find({}, {email:1, role:1}).pretty()
db.templates.find({status:"APPROVED"}).count()
db.usage_daily_rollup.find().sort({day:-1}).limit(5)

# Drop and recreate database (full reset)
use whatsapp_saas
db.dropDatabase()
```

### Make Commands

```bash
make install    # Install all dependencies (backend + frontend)
make dev        # Start all 3 services in background
make stop       # Stop all background services
make logs       # Tail all logs
make seed       # Run demo data seeder
make clean      # Remove node_modules, venv, __pycache__
make reset-db   # Drop and recreate the database
make test       # Run all tests
```

---

## 14. Troubleshooting

### ❌ MongoDB connection refused

**Error:** `pymongo.errors.ServerSelectionTimeoutError: localhost:27017`

**Fix:**
```bash
# Check if MongoDB is running
brew services list | grep mongodb

# Start it
brew services start mongodb-community@7.0

# Or check the MongoDB log
cat /opt/homebrew/var/log/mongodb/mongo.log | tail -20
```

---

### ❌ Python package install fails — `error: legacy-install-failure`

**Error:** Occurs with bcrypt, cryptography

**Fix:**
```bash
# Install Xcode command line tools
xcode-select --install

# Then retry
pip install bcrypt cryptography
```

---

### ❌ `qrcode` module not found

**Fix:**
```bash
pip install qrcode[pil]
```

---

### ❌ Frontend won't start — Port 3000 in use

**Error:** `Something is already running on port 3000`

**Fix:**
```bash
# Find what's using port 3000
lsof -i :3000

# Kill it
kill -9 $(lsof -ti:3000)

# Or use a different port
PORT=3001 yarn start
# Update CORS_ORIGINS in backend .env to http://localhost:3001
```

---

### ❌ Backend port 8001 in use

**Fix:**
```bash
lsof -i :8001
kill -9 $(lsof -ti:8001)
```

---

### ❌ `TOKEN_ENCRYPTION_KEY` is not a valid Fernet key

**Error:** `ValueError: Fernet key must be 32 url-safe base64-encoded bytes`

**Fix:** Regenerate the key:
```bash
python3.11 -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

---

### ❌ CORS error in browser — `Access-Control-Allow-Origin`

**Error:** Browser console shows CORS error

**Fix:** Ensure `CORS_ORIGINS` in backend `.env` matches your frontend URL exactly:
```ini
CORS_ORIGINS=http://localhost:3000
```
Restart the backend after changing `.env`.

---

### ❌ Login succeeds via curl but fails in browser

**Cause:** Cookies with `SameSite=None; Secure` require HTTPS in some browsers.

**Fix for local development:**

Option A — Use HTTP (already configured in local setup above).

Option B — Enable the `httpOnly` Secure=False workaround for local:
```bash
# In backend/.env, this is already handled — local uses SameSite=Lax
# Nothing to change for localhost
```

Option C — Use Chrome with disabled security (testing only):
```bash
open -na "Google Chrome" --args --disable-features=SameSiteByDefaultCookies --user-data-dir=/tmp/chrome-dev
```

---

### ❌ Hot-reload not working

**Fix:** Make sure you're running with `--reload` flag:
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

### ❌ `yarn install` fails on Apple Silicon (M1/M2/M3)

**Error:** Architecture mismatch for native modules

**Fix:**
```bash
# Install Node.js natively for arm64
arch -arm64 brew install node@20

# Clear cache and reinstall
rm -rf node_modules yarn.lock
arch -arm64 yarn install
```

---

### ❌ Template sync fails with 401

This is expected in mock mode — the seeded demo WABAs use a fake token. Only real WABAs connected via Embedded Signup will sync successfully.

---

### ❌ WebSocket closes immediately

**Fix:** Check that the `access_token` cookie exists. Login first via the browser or curl, then the WebSocket will authenticate automatically using the cookie.

---

## Appendix — Quick Reference Card

```
┌──────────────────────────────────────────────────────────────┐
│              Local Development Quick Reference               │
├──────────────────────────────────────────────────────────────┤
│  Frontend URL    http://localhost:3000                        │
│  Backend URL     http://localhost:8001                        │
│  API Docs        http://localhost:8001/docs                   │
│  MongoDB         mongodb://localhost:27017/whatsapp_saas      │
│  WebSocket       ws://localhost:8001/api/ws/inbox             │
├──────────────────────────────────────────────────────────────┤
│  Demo login      owner@demo.com / Owner123!                   │
│  Super admin     super@admin.com / SuperAdmin123!             │
│                  (MFA required — scan QR on first login)      │
├──────────────────────────────────────────────────────────────┤
│  Start MongoDB   brew services start mongodb-community@7.0    │
│  Start Backend   uvicorn server:app --port 8001 --reload      │
│  Start Frontend  yarn start                                   │
│  Seed data       python seed_demo_data.py                     │
├──────────────────────────────────────────────────────────────┤
│  Health check    curl http://localhost:8001/api/health        │
│  System info     curl http://localhost:8001/api/system/info   │
└──────────────────────────────────────────────────────────────┘
```

---

*WhatsApp Business Management Platform · Local Setup Guide · July 2026*
