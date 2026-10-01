# Database Backup & Recovery Procedures

MachIntel utilizes standard PostgreSQL binary dump formats (`pg_dump` with custom binary format `-F c`) for zero-loss, atomic snapshots of operational and analytical data.

---

## 1. Creating a Local Backup

To create an atomic snapshot:

```bash
# Using Makefile
make backup

# Or using the utility script directly
./scripts/backup_db.sh
```

### Output
Backups are timestamped and saved into `storage/backups/`:
```
storage/backups/machintel_backup_YYYYMMDD_HHMMSS.dump
```
A complete database dump containing 200 turbofans, 33,727 telemetry cycles, 233 predictions, 1,392 evidence records, and background job histories requires approximately **3.0 MB**.

---

## 2. Restoring a Backup

To restore an existing backup into a database:

```bash
# General syntax:
./scripts/restore_db.sh <backup_file_path> [target_database_name]

# Example: Restore into the default database
./scripts/restore_db.sh storage/backups/machintel_backup_20261002_000133.dump machintel

# Example: Restore into an isolated database for audit
./scripts/restore_db.sh storage/backups/machintel_backup_20261002_000133.dump machintel_audit_db
```

The restore script automatically:
1. Verifies the backup archive integrity.
2. Creates the target database if it does not already exist.
3. Invokes `pg_restore` with clean flags (`--clean --if-exists --no-owner`).

---

## 3. Automated Validation Test Results (M13 Audit)

The backup and restore procedure was validated against an isolated test database `machintel_test_restore_m13`:

| Dimension | Primary Database (`machintel`) | Restored Database (`machintel_test_restore_m13`) | Verification Status |
|---|---|---|---|
| **Alembic Revision** | `f3a4b5c6d7e8` | `f3a4b5c6d7e8` | **VERIFIED MATCH** ✅ |
| **Machines Ingested** | 200 units | 200 units | **VERIFIED MATCH** ✅ |
| **Telemetry Cycles** | 33,727 records | 33,727 records | **VERIFIED MATCH** ✅ |
| **Predictions** | 233 records | 233 records | **VERIFIED MATCH** ✅ |
| **Evidence Items** | 1,392 records | 1,392 records | **VERIFIED MATCH** ✅ |
| **Work Orders** | 1 record | 1 record | **VERIFIED MATCH** ✅ |
| **Background Jobs** | 1 record | 1 record | **VERIFIED MATCH** ✅ |

The temporary test database was dropped immediately after verification without affecting the primary system.
