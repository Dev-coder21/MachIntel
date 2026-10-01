# Evidence Object Model

## 1. Schema Definition

The evidence model is implemented using PostgreSQL tables and SQLAlchemy 2.0 ORM mappings in `backend/app/models/evidence.py`.

### 1.1 `evidence_records` Table
| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID (PK) | No | Primary identifier |
| `domain` | VARCHAR(50) | No | `MACHINE_HEALTH` or `VISUAL_INSPECTION` |
| `entity_type` | VARCHAR(50) | No | `MACHINE`, `PREDICTION`, `RISK_ASSESSMENT`, `ALERT`, `INSPECTION_RUN`, `INSPECTION_RESULT` |
| `entity_id` | VARCHAR(100) | No | Authoritative entity ID / Foreign key reference |
| `evidence_type` | VARCHAR(50) | No | Category of evidence payload |
| `source` | VARCHAR(100) | No | Originating storage table |
| `source_reference` | VARCHAR(255) | No | Query / filter key locating source |
| `observation_cycle`| INTEGER | Yes | Preserved cycle counter (C-MAPSS only) |
| `observation_time` | TIMESTAMPTZ | Yes | Real timestamp (Visual inspection / system only) |
| `value` | JSONB | Yes | Structured payload values |
| `unit` | VARCHAR(50) | Yes | Unit of measurement |
| `confidence` | FLOAT | Yes | Calibrated probability/confidence (strictly null if uncalibrated) |
| `quality_state` | VARCHAR(50) | No | `VERIFIED`, `DERIVED`, `BENCHMARK_GROUND_TRUTH`, `PROVENANCE_ONLY`, `UNAVAILABLE` |
| `explanation` | TEXT | Yes | Generated natural language summary |
| `provenance` | JSONB | No | Full provenance metadata dictionary |
| `model_version` | VARCHAR(100) | Yes | Specific ML/CV model version |
| `feature_version` | VARCHAR(100) | Yes | Feature configuration version |
| `policy_version` | VARCHAR(100) | Yes | Operational policy version |
| `created_at` | TIMESTAMPTZ | No | Ledger write timestamp |

Indexes:
- `ix_evidence_domain` on `domain`
- `ix_evidence_entity_type` on `entity_type`
- `ix_evidence_entity_id` on `entity_id`
- `ix_evidence_type` on `evidence_type`
- `ix_evidence_source` on `source`
- `ix_evidence_cycle` on `observation_cycle`
- `ix_evidence_created_at` on `created_at`
- `ix_evidence_model_ver` on `model_version`
- `ix_evidence_policy_ver` on `policy_version`
- `ix_evidence_lookup` composite on `(domain, entity_type, entity_id)`

---

## 2. Quality & Trust States

1. **`VERIFIED`**:
   - Direct raw sensor observation or image asset.
   - Example: C-MAPSS telemetry cycle reading; raw MVTec test PNG capture.
2. **`DERIVED`**:
   - Mathematically transformed feature, statistical aggregation, or model inference.
   - Example: Rolling slope features; RUL regression prediction; PatchCore distance score; deterministic risk state.
3. **`BENCHMARK_GROUND_TRUTH`**:
   - Official test set ground truth provided strictly for offline validation.
   - Example: MVTec AD ground truth defect mask and test label.
   - **Crucial Rule**: The ML pipeline is isolated with zero leakage during operational inference.
4. **`PROVENANCE_ONLY`**:
   - Metadata record describing model architecture, dataset split boundaries, or operational policies.
5. **`UNAVAILABLE`**:
   - Placeholder indicating an expected evidence node could not be calculated or recorded.
