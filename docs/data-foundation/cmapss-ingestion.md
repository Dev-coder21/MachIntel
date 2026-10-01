# NASA C-MAPSS FD001 Ingestion Pipeline

## 1. Overview & Dataset Source
MachIntel Milestone M2 establishes the production-grade data foundation for machine health intelligence using the official **NASA C-MAPSS FD001** (Commercial Modular Aero-Propulsion System Simulation) benchmark dataset.

- **Dataset Identifier:** `NASA-C-MAPSS-FD001`
- **Origin:** NASA Prognostics Center of Excellence (PCoE)
- **Primary Source:** Saxena, A., Goebel, K., Simon, D., & Eklund, N. (2008). *Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation.*
- **Operating Regime:** Sea level, single operational regime (Nominal sea level flight).
- **Failure Mode:** High-Pressure Compressor (HPC) degradation.

---

## 2. Ingested Entity & Record Totals

| Category | File | Description | Engine Units | Ingested Cycles |
| :--- | :--- | :--- | :--- | :--- |
| **Training Engines** | `train_FD001.txt` | Run-to-failure turbofan engines | Units 1–100 | 20,631 cycles |
| **Test Engines** | `test_FD001.txt` | Censored test engines prior to failure | Test Units 1–100 | 13,096 cycles |
| **Ground Truth RUL** | `RUL_FD001.txt` | Official remaining useful life vector | Units 1–100 | 100 values |
| **Total Ingested** | — | **Full FD001 Dataset** | **200 Engines** | **33,727 Cycles** |

---

## 3. Storage Hierarchy
Raw datasets are preserved in their exact unmodified form in local storage:

```
data/
  raw/
    cmapss/
      FD001/
        train_FD001.txt      # 20,631 rows, 3,515,356 bytes
        test_FD001.txt       # 13,096 rows, 2,228,855 bytes
        RUL_FD001.txt        # 100 rows, 429 bytes
  processed/
    cmapss/
      FD001/
        .gitkeep             # Prepared for feature stores and ML preprocessors
```

Raw source files are protected by `.gitignore` rules and must never be committed directly to Git or mutated in place.

---

## 4. Pipeline Execution & CLI

Ingestion is executed via a CLI script designed for automated setups:

```bash
# Ingest official NASA C-MAPSS FD001 files into PostgreSQL
python -m backend.scripts.ingest_cmapss --dataset FD001
```

### Pipeline Architecture:
1. **File Location & Verification:** Locates `train_FD001.txt`, `test_FD001.txt`, and `RUL_FD001.txt`. Computes SHA-256 digests and file sizes.
2. **Schema & Integrity Validation:** Runs `DataQualityValidator` ensuring 26 space-separated columns, numeric types, monotonic cycles, and non-empty rows.
3. **Channel Invariance Detection:** Computes channel variance $\sigma^2$ across training cycles, detecting invariant channels (`op_setting_3`, sensors 1, 5, 10, 16, 18, 19).
4. **Dataset Metadata Creation/Update:** Upserts `dataset_metadata` row capturing SHA-256 digests, active/invariant sensor lists, and schema versions.
5. **Machine Entity Provisioning:** Upserts 100 training machines (`TURBOFAN-ENG-001` to `100`) and 100 test machines (`TURBOFAN-ENG-TEST-001` to `100`) with cycle counts and split policies.
6. **Telemetry Bulk Ingestion:** Bulk inserts 33,727 telemetry records via chunked PostgreSQL `ON CONFLICT DO NOTHING` statements (preserving unit_id and source_cycle).
7. **Quality Audit Logging:** Records formal `data_quality_issues` entries for identified invariant channels.

---

## 5. Safe Repeatability & Idempotency
The ingestion service is **strictly idempotent**:
- Machine entities are identified by `(source_dataset, source_entity_id)` with unique database constraints.
- Telemetry records are uniquely constrained by `(machine_id, source_cycle, split_type)`.
- Re-running `python -m backend.scripts.ingest_cmapss --dataset FD001` completes cleanly without creating duplicate records or throwing constraint violations.
- Verified by automated backend test `test_ingestion_service_idempotency`.

---

## 6. How to Reproduce Ingestion from Scratch
1. Start the PostgreSQL 16 database:
   ```bash
   docker compose up -d postgres
   ```
2. Run database migrations:
   ```bash
   cd backend && .venv/bin/alembic upgrade head
   ```
3. Verify or download raw C-MAPSS files:
   ```bash
   .venv/bin/python backend/scripts/download_cmapss.py
   ```
4. Run the ingestion pipeline:
   ```bash
   .venv/bin/python -m backend.scripts.ingest_cmapss --dataset FD001
   ```
5. Confirm ingestion via API:
   ```bash
   curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/machines/stats/summary
   ```
