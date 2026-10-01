# Telemetry Schema & Entity Relations

## 1. Relational Schema Architecture

MachIntel stores C-MAPSS telemetry across four interconnected PostgreSQL tables migrated with Alembic:
1. `dataset_metadata` (Dataset lineage, checksums, active sensor lists)
2. `machines` (Asset entities with split policy, operational status, cycle bounds)
3. `telemetry_records` (High-density structured sensor records per cycle)
4. `data_quality_issues` (Validation findings and channel invariance records)

---

## 2. Table Specifications

### A. `machines`
Represents physical/simulated industrial machinery assets.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key, Indexed | Machine surrogate identifier |
| `machine_id` | `VARCHAR(50)` | Unique, Indexed, NOT NULL | Business asset identifier (e.g. `TURBOFAN-ENG-001`) |
| `name` | `VARCHAR(100)` | NOT NULL | Human-readable asset description |
| `machine_type` | `VARCHAR(50)` | NOT NULL | Enum: `TURBOFAN_ENGINE`, `OPTICAL_INSPECTION_STATION` |
| `source_dataset` | `VARCHAR(100)` | NOT NULL, Indexed | Origin dataset (e.g. `NASA C-MAPSS (FD001)`) |
| `source_entity_id`| `VARCHAR(50)` | NOT NULL | Original engine unit number (e.g. `1`) |
| `dataset_id` | `UUID` | Foreign Key (`dataset_metadata.id`) | Provenance link |
| `status` | `VARCHAR(30)` | NOT NULL | Enum: `OPERATIONAL`, `MAINTENANCE`, `DEGRADED`, `OFFLINE` |
| `split_category` | `VARCHAR(30)` | NOT NULL, Indexed | Enum: `INTERNAL_TRAIN`, `INTERNAL_VAL`, `EVAL_TEST` |
| `total_cycles` | `INTEGER` | NOT NULL | Total recorded telemetry cycles |
| `max_cycle` | `INTEGER` | NOT NULL | Highest ingested cycle number |
| `ground_truth_rul`| `INTEGER` | NULL | Official ground-truth RUL (Test units only) |
| `metadata_json` | `JSON` | NOT NULL | Extensible machine metadata |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | Modification timestamp |

**Indexes & Constraints:**
- `uq_machine_source`: UNIQUE(`source_dataset`, `source_entity_id`)
- `ix_machines_machine_id`: INDEX(`machine_id`)
- `ix_machines_split_category`: INDEX(`split_category`)

---

### B. `telemetry_records`
Stores structured operational and sensor channels per flight cycle.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key, Indexed | Record UUID |
| `machine_id` | `UUID` | Foreign Key (`machines.id`), Indexed | Referenced asset entity |
| `source_cycle` | `INTEGER` | NOT NULL, Indexed | Authoritative engine operating flight cycle |
| `event_timestamp` | `TIMESTAMPTZ` | NULL | Wall-clock timestamp (`NULL` for C-MAPSS cycle data) |
| `split_type` | `VARCHAR(20)` | NOT NULL | `train` or `test` |
| `op_setting_1` | `DOUBLE PRECISION` | NOT NULL | Operational condition 1 (Mach number) |
| `op_setting_2` | `DOUBLE PRECISION` | NOT NULL | Operational condition 2 (Throttle TRA) |
| `op_setting_3` | `DOUBLE PRECISION` | NOT NULL | Operational condition 3 (Invariant: 100.0) |
| `sensor_1` .. `sensor_21` | `DOUBLE PRECISION` | NOT NULL | 21 thermodynamic engine sensor channels |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Ingestion timestamp |

**Indexes & Constraints:**
- `uq_telemetry_machine_cycle`: UNIQUE(`machine_id`, `source_cycle`, `split_type`)
- `ix_telemetry_machine_cycle`: INDEX(`machine_id`, `source_cycle` ASC)

---

### C. `dataset_metadata`
Stores formal provenance records.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key |
| `dataset_name` | `VARCHAR(100)` | Unique dataset name (`NASA C-MAPSS FD001`) |
| `dataset_identifier` | `VARCHAR(50)` | Canonical code (`NASA-C-MAPSS-FD001`) |
| `source` | `VARCHAR(255)` | Data source institute |
| `source_url` | `VARCHAR(500)` | Authoritative retrieval reference |
| `license` | `VARCHAR(100)` | Dataset license (NASA Open Source / Public Domain) |
| `retrieval_date` | `TIMESTAMPTZ` | Timestamp when files were validated and stored |
| `file_checksums` | `JSON` | Map of filenames to file sizes and SHA-256 hashes |
| `schema_version` | `VARCHAR(50)` | Telemetry schema version (`1.0.0`) |
| `preprocessing_version` | `VARCHAR(50)` | Preprocessor release version (`1.0.0`) |
| `ingestion_version` | `VARCHAR(50)` | Ingestion pipeline version (`1.0.0`) |
| `active_sensors` | `JSON` | List of non-zero variance sensor keys |
| `invariant_sensors` | `JSON` | List of invariant sensor keys ($\sigma = 0$) |

---

## 3. Strict Timestamp Policy
C-MAPSS FD001 is a cycle-based operational simulation. In compliance with MachIntel core guidelines:
- **`source_cycle`** represents the authoritative chronological progression of each engine.
- **`event_timestamp`** is strictly stored as `NULL`.
- No synthetic or arbitrary wall-clock timestamps (e.g. `2026-09-01 10:00:00`) are fabricated.
