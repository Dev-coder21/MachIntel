# ==============================================================================
# MachIntel — Operational Automation Makefile
# ==============================================================================
# Provides deterministic one-command developer workflows for packaging,
# startup, testing, database migrations, backups, and health verification.
# ==============================================================================

.PHONY: help build up down restart logs status migrate test test-backend test-frontend create-admin backup restore reset clean

SHELL := /bin/bash
PYTHON := backend/.venv/bin/python
PYTEST := backend/.venv/bin/pytest
ALEMBIC := backend/.venv/bin/alembic

help:
	@echo "======================================================================"
	@echo "MachIntel — Multimodal AI for Predictive Maintenance & Inspection"
	@echo "======================================================================"
	@echo "Available commands:"
	@echo "  make build         - Build production-ready Docker container images"
	@echo "  make up            - Launch stack in background (Docker or native)"
	@echo "  make down          - Gracefully stop active services"
	@echo "  make restart       - Restart backend, worker, and frontend"
	@echo "  make logs          - Tail service logs (docker compose logs -f)"
	@echo "  make status        - Run stack verification and probe health endpoints"
	@echo "  make migrate       - Apply latest database migrations (alembic head)"
	@echo "  make test          - Run complete test suite (backend + frontend)"
	@echo "  make test-backend  - Run 179 backend pytest suite"
	@echo "  make test-frontend - Run 62 frontend vitest suite"
	@echo "  make create-admin  - Run interactive administrative bootstrap CLI"
	@echo "  make backup        - Create atomic binary PostgreSQL dump"
	@echo "  make restore       - Restore latest database dump into target DB"
	@echo "  make reset         - [DESTRUCTIVE] Full database and container reset"
	@echo "======================================================================"

build:
	@if command -v docker &> /dev/null; then \
		echo "[INFO] Building Docker images..."; \
		docker compose build; \
	else \
		echo "[INFO] Building frontend production bundle natively..."; \
		cd frontend && npm run build; \
	fi

up:
	@if command -v docker &> /dev/null; then \
		echo "[INFO] Starting MachIntel stack with Docker Compose..."; \
		docker compose up -d; \
	else \
		echo "[INFO] Docker not detected. Please run native services:"; \
		echo "  1. Backend:  source backend/.venv/bin/activate && uvicorn backend.app.main:app --port 8000"; \
		echo "  2. Worker:   source backend/.venv/bin/activate && python -m backend.app.worker.worker"; \
		echo "  3. Frontend: cd frontend && npm run dev (or npm start)"; \
	fi

down:
	@if command -v docker &> /dev/null; then \
		docker compose down; \
	else \
		echo "[INFO] Stopping any background native worker or uvicorn processes..."; \
		pkill -f "python -m backend.app.worker.worker" 2>/dev/null || true; \
		pkill -f "uvicorn backend.app.main:app" 2>/dev/null || true; \
	fi

restart: down up

logs:
	@if command -v docker &> /dev/null; then \
		docker compose logs -f; \
	else \
		echo "[INFO] For native logs, monitor process stdout or backend logging."; \
	fi

status:
	@./scripts/verify_stack.sh

migrate:
	@echo "[INFO] Upgrading PostgreSQL database schema to latest Alembic head..."
	@$(ALEMBIC) -c backend/alembic.ini upgrade head

test: test-backend test-frontend

test-backend:
	@echo "[INFO] Executing comprehensive backend pytest suite (166 tests)..."
	@$(PYTEST) backend/tests/ -v

test-frontend:
	@echo "[INFO] Executing frontend vitest suite (57 tests) and typecheck..."
	@cd frontend && npm test && npx tsc --noEmit

create-admin:
	@$(PYTHON) backend/scripts/create_first_admin.py

backup:
	@./scripts/backup_db.sh

restore:
	@./scripts/restore_db.sh $(BACKUP_FILE) $(TARGET_DB)

reset:
	@./scripts/reset_local.sh

clean:
	@echo "[INFO] Cleaning Python __pycache__ and build caches..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache frontend/.next
