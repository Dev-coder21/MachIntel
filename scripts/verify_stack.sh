#!/bin/bash
# ==============================================================================
# MachIntel Stack Health & Verification Utility
# ==============================================================================
# Probes local database, backend API, worker health, and frontend availability.
# ==============================================================================

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
DB_NAME="${POSTGRES_DB:-machintel}"
DB_USER="${POSTGRES_USER:-$USER}"

echo "===================================================================="
echo "🔍 MACHINTEL LOCAL STACK VERIFICATION"
echo "===================================================================="

# 1. Database Connectivity
echo -n "[1/5] PostgreSQL Database (${DB_NAME}): "
if psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo "CONNECTED ✅"
else
    echo "UNREACHABLE ❌"
fi

# 2. Database Migration Status
echo -n "[2/5] Alembic Migration Revision: "
if [ -f "backend/.venv/bin/activate" ]; then
    source backend/.venv/bin/activate
fi
REV=$(alembic -c backend/alembic.ini current 2>/dev/null | grep -E "head|\(head\)" || echo "UNKNOWN")
echo "$REV ✅"

# 3. Backend API Health
echo -n "[3/5] Backend Liveness Probe (${BACKEND_URL}/api/v1/health/liveness): "
HTTP_LIVE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/v1/health/liveness" || echo "000")
if [ "$HTTP_LIVE" == "200" ]; then
    echo "HEALTHY (HTTP 200) ✅"
else
    echo "INACTIVE / NOT RUNNING (HTTP ${HTTP_LIVE}) ⚠️"
fi

echo -n "      Backend Readiness Probe (${BACKEND_URL}/api/v1/health/readiness): "
HTTP_READY=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/v1/health/readiness" || echo "000")
if [ "$HTTP_READY" == "200" ]; then
    echo "READY (HTTP 200) ✅"
else
    echo "NOT READY (HTTP ${HTTP_READY}) ⚠️"
fi

# 4. Worker Cluster Health
echo -n "[4/5] Background Worker Health Probe: "
if [ "$HTTP_READY" == "200" ]; then
    WORKER_STATUS=$(curl -s "${BACKEND_URL}/api/v1/jobs/health" | grep -o '"status":"[^"]*"' | cut -d':' -f2 | tr -d '"' || echo "UNKNOWN")
    echo "$WORKER_STATUS ✅"
else
    echo "PENDING BACKEND ⚠️"
fi

# 5. Frontend Web Availability
echo -n "[5/5] Frontend Web Server (${FRONTEND_URL}): "
HTTP_FE=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}" || echo "000")
if [ "$HTTP_FE" == "200" ] || [ "$HTTP_FE" == "307" ] || [ "$HTTP_FE" == "308" ]; then
    echo "ACTIVE (HTTP ${HTTP_FE}) ✅"
else
    echo "INACTIVE / NOT RUNNING (HTTP ${HTTP_FE}) ⚠️"
fi

echo "===================================================================="
