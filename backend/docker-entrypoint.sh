#!/bin/bash
set -e

# Function to wait for PostgreSQL database connectivity
wait_for_postgres() {
    echo "[INFO] Verifying PostgreSQL database readiness..."
    python - <<'EOF'
import sys
import time
import os
from sqlalchemy import create_engine, text

db_url = os.getenv("DATABASE_URL", "postgresql://machintel_user:machintel_password@postgres:5432/machintel")
max_retries = 30
retry_interval = 2

for attempt in range(1, max_retries + 1):
    try:
        engine = create_engine(db_url, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"[INFO] PostgreSQL connection verified on attempt {attempt}.")
        sys.exit(0)
    except Exception as e:
        if attempt % 5 == 0:
            print(f"[WARN] Database connection attempt {attempt}/{max_retries} waiting: {e}")
        time.sleep(retry_interval)

print("[ERROR] Could not connect to PostgreSQL database after timeout.")
sys.exit(1)
EOF
}

case "$1" in
    api)
        wait_for_postgres
        echo "[INFO] Applying Alembic database migrations (upgrade head)..."
        alembic upgrade head
        echo "[INFO] Starting MachIntel FastAPI Application..."
        exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
        ;;
    worker)
        wait_for_postgres
        echo "[INFO] Starting MachIntel Background Worker Daemon..."
        exec python -m backend.app.worker.worker
        ;;
    *)
        exec "$@"
        ;;
esac
