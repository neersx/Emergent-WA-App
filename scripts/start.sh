#!/usr/bin/env bash
# start.sh — Start all services (MongoDB + Backend + Frontend) in one terminal
# Run from project root: ./scripts/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOG_DIR="/tmp/waba-logs"
VENV="$BACKEND_DIR/venv"

# ─── Colours ─────────────────────────────────────────────────────
CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; RESET='\033[0m'

echo ""
echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  ${CYAN}   WhatsApp Business Platform — Start All Services${RESET}"
echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

mkdir -p "$LOG_DIR"

# ─── Cleanup on exit ─────────────────────────────────────────────
cleanup() {
    echo ""
    echo -e "  ${YELLOW}Stopping all services...${RESET}"
    [ -f /tmp/waba-backend.pid ] && kill "$(cat /tmp/waba-backend.pid)" 2>/dev/null; rm -f /tmp/waba-backend.pid
    [ -f /tmp/waba-frontend.pid ] && kill "$(cat /tmp/waba-frontend.pid)" 2>/dev/null; rm -f /tmp/waba-frontend.pid
    echo -e "  ${GREEN}✅ All services stopped.${RESET}"
    echo ""
}
trap cleanup EXIT INT TERM

# ─── Check .env files ─────────────────────────────────────────────
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "  ${RED}❌ backend/.env not found.${RESET}"
    echo "  Run: ./scripts/setup-env.sh"
    exit 1
fi
if [ ! -f "$FRONTEND_DIR/.env" ]; then
    echo -e "  ${RED}❌ frontend/.env not found.${RESET}"
    echo "  Run: ./scripts/setup-env.sh"
    exit 1
fi

# ─── Check virtual environment ────────────────────────────────────
if [ ! -f "$VENV/bin/uvicorn" ]; then
    echo -e "  ${RED}❌ Python venv not set up.${RESET}"
    echo "  Run: make install"
    exit 1
fi

# ─── Check node_modules ──────────────────────────────────────────
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "  ${RED}❌ Frontend dependencies not installed.${RESET}"
    echo "  Run: make install"
    exit 1
fi

# ─── 1. MongoDB ───────────────────────────────────────────────────
echo -e "  ${CYAN}[1/3] Starting MongoDB...${RESET}"
brew services start mongodb-community@7.0 2>/dev/null || true
sleep 2
if mongosh --eval "db.runCommand({connectionStatus:1})" --quiet 2>/dev/null | grep -q '"ok" : 1'; then
    echo -e "  ${GREEN}      ✅ MongoDB running on port 27017${RESET}"
else
    echo -e "  ${RED}      ❌ MongoDB failed to start. Check: brew services list${RESET}"
    exit 1
fi

# ─── 2. Backend ───────────────────────────────────────────────────
echo -e "  ${CYAN}[2/3] Starting FastAPI backend on :8001...${RESET}"
cd "$BACKEND_DIR"
"$VENV/bin/uvicorn" server:app --host 0.0.0.0 --port 8001 --reload \
    > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/waba-backend.pid
sleep 4

# Check if backend started
if kill -0 $BACKEND_PID 2>/dev/null && \
   curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}      ✅ Backend running on http://localhost:8001${RESET}"
else
    echo -e "  ${RED}      ❌ Backend failed to start. Check logs: tail -50 $LOG_DIR/backend.log${RESET}"
    cat "$LOG_DIR/backend.log" | tail -20
    exit 1
fi

# ─── 3. Frontend ──────────────────────────────────────────────────
echo -e "  ${CYAN}[3/3] Starting React frontend on :3000...${RESET}"
cd "$FRONTEND_DIR"
BROWSER=none yarn start > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > /tmp/waba-frontend.pid
echo -e "  ${GREEN}      ✅ Frontend starting (takes ~30s first time)...${RESET}"

# ─── Summary ──────────────────────────────────────────────────────
cd "$PROJECT_ROOT"
echo ""
echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${GREEN}🚀 All services started!${RESET}"
echo ""
echo "     Frontend   →  http://localhost:3000"
echo "     Backend    →  http://localhost:8001"
echo "     API Docs   →  http://localhost:8001/docs"
echo "     WebSocket  →  ws://localhost:8001/api/ws/inbox"
echo ""
echo "  Login:  owner@demo.com / Owner123!"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop all services${RESET}"
echo ""

# ─── Tail logs ────────────────────────────────────────────────────
tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
