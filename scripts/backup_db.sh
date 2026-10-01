#!/bin/bash
# ==============================================================================
# MachIntel Local Database Backup Utility
# ==============================================================================
# Creates an atomic, binary-format PostgreSQL dump of the active database.
# Preserves all machines, telemetry, predictions, risks, alerts, evidence,
# maintenance work orders, AI investigations, and background job records.
# ==============================================================================

set -e

BACKUP_DIR="${BACKUP_DIR:-storage/backups}"
mkdir -p "$BACKUP_DIR"

DB_NAME="${POSTGRES_DB:-machintel}"
DB_USER="${POSTGRES_USER:-$USER}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.dump"

echo "[INFO] Creating binary backup of database '${DB_NAME}' on ${DB_HOST}:${DB_PORT}..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -F c -b -v -f "$BACKUP_FILE" "$DB_NAME" 2>&1 | grep -v "^$" | head -n 20

echo ""
echo "===================================================================="
echo "✅ Database backup created successfully:"
echo "   $BACKUP_FILE"
echo "   Size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo "===================================================================="
