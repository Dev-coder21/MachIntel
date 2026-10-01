#!/bin/bash
# ==============================================================================
# MachIntel Local Database Restore Utility
# ==============================================================================
# Restores a binary PostgreSQL dump (.dump) into a specified target database.
# Usage:
#   ./scripts/restore_db.sh <backup_file_path> [target_database_name]
# ==============================================================================

set -e

BACKUP_FILE="$1"
TARGET_DB="${2:-machintel}"
DB_USER="${POSTGRES_USER:-$USER}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <path_to_backup_file> [target_database_name]"
    echo "Example: $0 storage/backups/machintel_backup_20261002_000000.dump machintel_test_restore"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] Backup file '$BACKUP_FILE' does not exist."
    exit 1
fi

echo "[INFO] Preparing target database '${TARGET_DB}' on ${DB_HOST}:${DB_PORT}..."

# Check if target database exists; if not, create it
EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'" || echo "0")

if [ "$EXISTS" != "1" ]; then
    echo "[INFO] Creating database '${TARGET_DB}'..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE ${TARGET_DB};"
else
    echo "[INFO] Database '${TARGET_DB}' already exists. Restoring contents..."
fi

echo "[INFO] Restoring '${BACKUP_FILE}' into '${TARGET_DB}'..."
pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TARGET_DB" --clean --if-exists --no-owner --no-privileges "$BACKUP_FILE" 2>&1 | grep -v "^$" | head -n 30 || true

echo ""
echo "===================================================================="
echo "✅ Database restore completed for '${TARGET_DB}'."
echo "===================================================================="
