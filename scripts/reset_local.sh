#!/bin/bash
# ==============================================================================
# MachIntel Local Reset Script (DESTRUCTIVE)
# ==============================================================================
# WARNING: This script terminates running MachIntel processes and wipes the local
# PostgreSQL database for a completely clean re-initialization.
# ==============================================================================

set -e

FORCE=false
if [ "$1" == "--force" ] || [ "$1" == "-f" ]; then
    FORCE=true
fi

echo "===================================================================="
echo "⚠️  WARNING: MACHINTEL LOCAL DATABASE & PROCESS RESET (DESTRUCTIVE)"
echo "===================================================================="
echo "This operation will:"
echo "  1. Stop background workers and FastAPI processes (if running locally)."
echo "  2. Terminate Docker Compose services and remove volumes (if active)."
echo "  3. Recreate a clean, empty PostgreSQL database for MachIntel."
echo ""

if [ "$FORCE" = false ]; then
    read -p "Are you sure you want to proceed with full reset? (yes/N): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "[INFO] Reset aborted by user."
        exit 0
    fi
fi

echo "[1/4] Stopping local background processes..."
pkill -f "python -m backend.app.worker.worker" 2>/dev/null || true
pkill -f "uvicorn backend.app.main:app" 2>/dev/null || true

if command -v docker &> /dev/null; then
    echo "[2/4] Stopping Docker containers and removing volumes..."
    docker compose down -v --remove-orphans 2>/dev/null || true
else
    echo "[2/4] Docker CLI not active on host. Proceeding with native PostgreSQL reset..."
fi

echo "[3/4] Re-initializing local PostgreSQL database..."
DB_NAME="${POSTGRES_DB:-machintel}"
DB_USER="${POSTGRES_USER:-$USER}"

# Terminate existing connections to allow drop
psql -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" 2>/dev/null || true
psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" 2>/dev/null || true
psql -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME};" 2>/dev/null || true

echo "[4/4] Applying fresh Alembic migrations..."
if [ -f "backend/.venv/bin/activate" ]; then
    source backend/.venv/bin/activate
fi
alembic -c backend/alembic.ini upgrade head

echo ""
echo "===================================================================="
echo "✅ MachIntel database successfully reset and migrated to head."
echo "===================================================================="
echo "Next steps:"
echo "  1. Ingest C-MAPSS telemetry: python backend/scripts/ingest_cmapss.py"
echo "  2. Create admin account:     python backend/scripts/create_first_admin.py"
echo "  3. Start services:           make up (or native python/node commands)"
echo "===================================================================="
