#!/usr/bin/env bash
# setup-env.sh — Generate .env files with secure cryptographic keys
# Run from project root: ./scripts/setup-env.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BACKEND_ENV="$PROJECT_ROOT/backend/.env"
FRONTEND_ENV="$PROJECT_ROOT/frontend/.env"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  WhatsApp Business Platform — Environment Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ─── Check Python ────────────────────────────────────────────────
if command -v python3.11 &> /dev/null; then
    PYTHON=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON=python3
else
    echo "❌ Python 3 not found. Install with: brew install python@3.11"
    exit 1
fi

# ─── Generate cryptographic keys ─────────────────────────────────
echo "🔑 Generating secure cryptographic keys..."

KEYS=$($PYTHON -c "
import secrets, base64
jwt_key = secrets.token_hex(32)
fernet_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
print(jwt_key)
print(fernet_key)
")

JWT_KEY=$(echo "$KEYS" | head -1)
FERNET_KEY=$(echo "$KEYS" | tail -1)

echo "   JWT_SIGNING_KEY     generated ✓"
echo "   TOKEN_ENCRYPTION_KEY generated ✓"

# ─── Create backend .env ──────────────────────────────────────────
if [ -f "$BACKEND_ENV" ]; then
    echo ""
    read -p "⚠️  backend/.env already exists. Overwrite? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "   Skipping backend/.env"
    else
        CREATE_BACKEND=true
    fi
else
    CREATE_BACKEND=true
fi

if [ "$CREATE_BACKEND" = "true" ]; then
    cat > "$BACKEND_ENV" << EOF
# Database
MONGO_URL=mongodb://localhost:27017
DB_NAME=whatsapp_saas

# CORS — allow local frontend
CORS_ORIGINS=http://localhost:3000

# Security — auto-generated (do NOT commit to git)
JWT_SIGNING_KEY=$JWT_KEY
TOKEN_ENCRYPTION_KEY=$FERNET_KEY

# Meta WhatsApp API
# Set META_MOCK_MODE=true to run without real Meta credentials
META_APP_ID=
META_APP_SECRET=
META_EMBEDDED_SIGNUP_CONFIG_ID=
META_WEBHOOK_VERIFY_TOKEN=local-dev-verify-token
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
    echo "   ✅ backend/.env created"
fi

# ─── Create frontend .env ─────────────────────────────────────────
if [ -f "$FRONTEND_ENV" ]; then
    echo ""
    read -p "⚠️  frontend/.env already exists. Overwrite? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "   Skipping frontend/.env"
    else
        CREATE_FRONTEND=true
    fi
else
    CREATE_FRONTEND=true
fi

if [ "$CREATE_FRONTEND" = "true" ]; then
    cat > "$FRONTEND_ENV" << EOF
REACT_APP_BACKEND_URL=http://localhost:8001
EOF
    echo "   ✅ frontend/.env created"
fi

# ─── Ensure .env is in .gitignore ────────────────────────────────
GITIGNORE="$PROJECT_ROOT/.gitignore"
if [ -f "$GITIGNORE" ]; then
    if ! grep -q "^\.env$" "$GITIGNORE" 2>/dev/null; then
        echo "" >> "$GITIGNORE"
        echo ".env" >> "$GITIGNORE"
        echo "   ✅ Added .env to .gitignore"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Environment setup complete!"
echo ""
echo "  Next steps:"
echo "  1. For mock mode (no Meta credentials):   make dev"
echo "  2. For live mode: edit backend/.env and"
echo "     set META_APP_ID, META_APP_SECRET, etc."
echo "     then: META_MOCK_MODE=false"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
