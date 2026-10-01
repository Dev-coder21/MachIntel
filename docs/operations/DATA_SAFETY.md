# Data Safety, Retention & Backup Strategy (Local & On-Premises)

## 1. Overview
MachIntel is designed to operate as a local/on-premises multimodal predictive maintenance and industrial inspection intelligence platform. To maintain data safety, business continuity, and auditability without cloud-bound dependencies, this document defines asset classification, backup scopes, and recovery procedures.

---

## 2. Asset Classification & Provenance

| Asset Category | Location | State Type | Source Controlled? | Reproducible? | Backup Criticality |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Source Code & Migrations** | Git repository (`/backend`, `/frontend`, `/docs`) | Immutable / Versioned | Yes | Yes (from Git) | Handled by Git VCS |
| **PostgreSQL Database** | PostgreSQL 16 (`machintel` DB) | Mutable / Transactional | No | No (contains live audit logs, annotations, work orders) | **Tier 1 (Mandatory Daily)** |
| **Inspection Visual Artifacts** | `storage/inspections/` (heatmaps, overlays) | Generated Artifacts | No | Partially (via re-evaluating PatchCore) | **Tier 2 (Recommended Weekly)** |
| **Trained ML & CV Models** | `backend/app/services/models/`, `storage/models/` | Model Weights (`.joblib`, `.pt`) | No | Yes (via local training pipelines) | **Tier 2 (Recommended on model update)** |
| **Raw Ingested Datasets** | `data/raw/` (NASA C-MAPSS, MVTec AD) | Static Raw Data | No | Yes (public benchmarks) | **Tier 3 (Reproducible)** |
| **Environment Configuration** | `.env` | Secret / Config | No (gitignored) | No (contains secrets) | **Tier 1 (Encrypted Backup)** |

---

## 3. What is Gitignored vs. Preserved

### Strictly Gitignored (Excluded from Version Control):
- `.env`, `.env.local`, `.env.*.local` (local secrets, credentials, tokens)
- `data/*` (raw datasets exceeding Git file limits)
- `storage/*` (generated PatchCore heatmaps, masks, memory banks)
- `backend/.venv/`, `frontend/node_modules/`, `frontend/.next/` (build and virtual environment artifacts)
- `.pytest_cache/`, `.coverage`, `coverage.xml` (test outputs)

### Preserved for System Reproducibility:
- `alembic/versions/*.py`: All 8 Alembic schema migration files.
- `backend/app/db/seeds/`: Seed scripts for initial machines, sensors, and users.
- `backend/scripts/`: Admin bootstrap and verification utilities.
- `docs/`: Threat model, hardening baseline, and architectural blueprints.

---

## 4. Recommended Local Backup Procedures

### A. PostgreSQL Logical Dump (Daily Automated)
The relational database contains machine records, telemetry cycles, predictions, risk assessments, operational alerts, audit events, and maintenance work orders.
```bash
# Recommended backup command (executed via cron on host machine)
pg_dump -U devtrivedi -h localhost -p 5432 -F c -b -v -f "/backup/machintel/machintel_$(date +%Y%m%d_%H%M%S).dump" machintel
```

### B. Storage Artifacts Archive (Weekly)
To preserve visual inspection heatmaps and PatchCore localization overlays without re-running full inference:
```bash
tar -czvf "/backup/machintel/storage_inspections_$(date +%Y%m%d).tar.gz" storage/inspections/
```

### C. Configuration & Secrets Safe Vault
Keep an encrypted copy of `.env` in an offsite key management or secure vault:
```bash
# Example using GPG symmetric encryption
gpg --symmetric --cipher-algo AES256 -o .env.encrypted .env
```

---

## 5. Recovery & Disaster Recovery Plan

1. **Host Provisioning**: Install Python 3.13, Node.js 18+, and PostgreSQL 16.
2. **Repository Clone**: Clone repository from Git.
3. **Database Restore**:
   ```bash
   createdb -U devtrivedi machintel
   pg_restore -U devtrivedi -d machintel -v /backup/machintel/machintel_YYYYMMDD.dump
   ```
4. **Migration Verification**:
   ```bash
   cd backend
   alembic upgrade head
   ```
5. **Storage Unpack**:
   ```bash
   tar -xzvf /backup/machintel/storage_inspections_YYYYMMDD.tar.gz -C .
   ```
6. **Environment Hydration**: Restore `.env` from encrypted vault and restart services.
