# WhatsApp Business Platform — Makefile
# Usage: make <target>

.PHONY: help install dev stop logs seed clean reset-db test check-deps backend frontend mongo

BACKEND_DIR  := backend
FRONTEND_DIR := frontend
VENV         := $(BACKEND_DIR)/venv
PYTHON       := $(VENV)/bin/python3
PIP          := $(VENV)/bin/pip
UVICORN      := $(VENV)/bin/uvicorn

# Colours
CYAN  := \033[0;36m
GREEN := \033[0;32m
RESET := \033[0m

help: ## Show this help message
	@echo ""
	@echo "  $(CYAN)WhatsApp Business Platform — Local Development$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ── Prerequisites ────────────────────────────────────────────────

check-deps: ## Check all required tools are installed
	@echo "$(CYAN)Checking dependencies...$(RESET)"
	@python3.11 --version 2>/dev/null || (echo "❌ Python 3.11 not found — brew install python@3.11" && exit 1)
	@node --version 2>/dev/null || (echo "❌ Node.js not found — brew install node@20" && exit 1)
	@yarn --version 2>/dev/null || (echo "❌ Yarn not found — npm install -g yarn" && exit 1)
	@mongod --version 2>/dev/null || (echo "❌ MongoDB not found — brew install mongodb-community@7.0" && exit 1)
	@echo "$(GREEN)✅ All prerequisites found$(RESET)"

# ── Installation ─────────────────────────────────────────────────

install: install-backend install-frontend ## Install all dependencies (backend + frontend)
	@echo "$(GREEN)✅ All dependencies installed$(RESET)"

install-backend: ## Install Python dependencies
	@echo "$(CYAN)Setting up Python virtual environment...$(RESET)"
	@test -d $(VENV) || python3.11 -m venv $(VENV)
	@$(PIP) install --upgrade pip -q
	@$(PIP) install -r $(BACKEND_DIR)/requirements.txt -q
	@echo "$(GREEN)✅ Backend dependencies installed$(RESET)"

install-frontend: ## Install Node.js dependencies
	@echo "$(CYAN)Installing frontend dependencies...$(RESET)"
	@cd $(FRONTEND_DIR) && yarn install --frozen-lockfile
	@echo "$(GREEN)✅ Frontend dependencies installed$(RESET)"

# ── Environment Setup ─────────────────────────────────────────────

setup-env: ## Generate .env files with secure keys
	@echo "$(CYAN)Generating environment files...$(RESET)"
	@chmod +x scripts/setup-env.sh && ./scripts/setup-env.sh
	@echo "$(GREEN)✅ .env files created$(RESET)"

# ── Running Services ──────────────────────────────────────────────

mongo: ## Start MongoDB (if not already running as a service)
	@echo "$(CYAN)Starting MongoDB...$(RESET)"
	@brew services start mongodb-community@7.0 2>/dev/null || \
	  mongod --dbpath /opt/homebrew/var/mongodb --fork --logpath /tmp/mongodb.log
	@sleep 2
	@mongosh --eval "db.runCommand({connectionStatus:1})" --quiet && \
	  echo "$(GREEN)✅ MongoDB running$(RESET)" || echo "❌ MongoDB failed to start"

backend: ## Start FastAPI backend (requires venv activated)
	@echo "$(CYAN)Starting backend on :8001...$(RESET)"
	@cd $(BACKEND_DIR) && $(UVICORN) server:app --host 0.0.0.0 --port 8001 --reload

frontend: ## Start React frontend on :3000
	@echo "$(CYAN)Starting frontend on :3000...$(RESET)"
	@cd $(FRONTEND_DIR) && yarn start

dev: ## Start all services in background (MongoDB + Backend + Frontend)
	@echo "$(CYAN)Starting all services...$(RESET)"
	@mkdir -p /tmp/waba-logs
	@brew services start mongodb-community@7.0 2>/dev/null; true
	@sleep 2
	@cd $(BACKEND_DIR) && $(UVICORN) server:app --host 0.0.0.0 --port 8001 --reload \
	  > /tmp/waba-logs/backend.log 2>&1 & echo $$! > /tmp/waba-backend.pid
	@sleep 3
	@cd $(FRONTEND_DIR) && yarn start \
	  > /tmp/waba-logs/frontend.log 2>&1 & echo $$! > /tmp/waba-frontend.pid
	@echo ""
	@echo "$(GREEN)✅ All services started!$(RESET)"
	@echo ""
	@echo "  Frontend  → http://localhost:3000"
	@echo "  Backend   → http://localhost:8001"
	@echo "  API Docs  → http://localhost:8001/docs"
	@echo ""
	@echo "  Run $(CYAN)make logs$(RESET) to view output"
	@echo "  Run $(CYAN)make stop$(RESET) to stop all services"
	@echo ""

stop: ## Stop all background services
	@echo "$(CYAN)Stopping services...$(RESET)"
	@-kill $$(cat /tmp/waba-backend.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/waba-backend.pid
	@-kill $$(cat /tmp/waba-frontend.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/waba-frontend.pid
	@-lsof -ti:8001 | xargs kill -9 2>/dev/null; true
	@-lsof -ti:3000 | xargs kill -9 2>/dev/null; true
	@echo "$(GREEN)✅ Services stopped$(RESET)"

restart: stop dev ## Restart all services

# ── Logs ──────────────────────────────────────────────────────────

logs: ## Tail all service logs
	@tail -f /tmp/waba-logs/backend.log /tmp/waba-logs/frontend.log 2>/dev/null || \
	  echo "No log files found — run 'make dev' first"

logs-backend: ## Tail backend logs only
	@tail -f /tmp/waba-logs/backend.log

logs-frontend: ## Tail frontend logs only
	@tail -f /tmp/waba-logs/frontend.log

# ── Database ──────────────────────────────────────────────────────

seed: ## Seed demo data (WABAs, phones, templates, messages, usage rollup)
	@echo "$(CYAN)Seeding demo data...$(RESET)"
	@cd $(BACKEND_DIR) && $(PYTHON) seed_demo_data.py
	@echo "$(GREEN)✅ Demo data seeded$(RESET)"

reset-db: ## ⚠️  Drop and recreate the database (ALL DATA LOST)
	@echo "⚠️  This will delete ALL data in whatsapp_saas database!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	@mongosh whatsapp_saas --eval "db.dropDatabase()" --quiet
	@echo "$(GREEN)✅ Database dropped. Restart the backend to re-seed.$(RESET)"

mongo-shell: ## Open MongoDB shell for whatsapp_saas
	@mongosh whatsapp_saas

# ── Testing ───────────────────────────────────────────────────────

test: test-backend ## Run all tests

test-backend: ## Run backend tests
	@echo "$(CYAN)Running backend tests...$(RESET)"
	@cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v

health: ## Check if all services are running
	@echo "$(CYAN)Health check...$(RESET)"
	@curl -sf http://localhost:8001/api/health | python3 -m json.tool && \
	  echo "$(GREEN)✅ Backend healthy$(RESET)" || echo "❌ Backend not responding"
	@curl -sf http://localhost:3000 > /dev/null && \
	  echo "$(GREEN)✅ Frontend healthy$(RESET)" || echo "❌ Frontend not responding"
	@mongosh --eval "db.runCommand({connectionStatus:1})" --quiet 2>/dev/null && \
	  echo "$(GREEN)✅ MongoDB healthy$(RESET)" || echo "❌ MongoDB not responding"

# ── Cleanup ───────────────────────────────────────────────────────

clean: ## Remove build artifacts (node_modules, venv, __pycache__)
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	@rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/build
	@rm -rf $(BACKEND_DIR)/venv $(BACKEND_DIR)/__pycache__
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; true
	@find . -name "*.pyc" -delete 2>/dev/null; true
	@echo "$(GREEN)✅ Cleaned$(RESET)"

open: ## Open app in browser
	@open http://localhost:3000

docs: ## Open the technical architecture docs
	@open http://localhost:3000/technical-architecture.html
