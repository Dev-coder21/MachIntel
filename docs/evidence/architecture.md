# Evidence Intelligence Architecture

## 1. Architectural Overview

The **Evidence Intelligence Layer (Milestone M8)** provides an immutable, causally traceable, and unified evidence abstraction across heterogeneous industrial datasets in **MachIntel**.

MachIntel integrates two distinct industrial observation domains:
1. **Domain A — Machine Health Intelligence**: NASA C-MAPSS FD001 turbofan degradation dataset (200 engine units, 33,727 operational telemetry cycles, temporally causal rolling-window feature engineering, RUL regression, Health Index normalizations, deterministic risk states, explainable reason codes, and operational alerts).
2. **Domain B — Visual Inspection Intelligence**: MVTec AD industrial visual inspection dataset (`metal_nut` category: 357 high-resolution imagery assets, PatchCore memory bank anomaly detection, 224x224 spatial heatmaps, pixel-level localization, and test ground truth benchmarks).

The architectural core is built on **strict domain separation**:
- **Zero Unsupported Multimodal Fusion**: C-MAPSS turbofan telemetry and MVTec `metal_nut` visual images represent completely different physical hardware domains and operational regimes.
- **No Fabricated Asset Links**: No entity links (`BELONGS_TO`, `DERIVED_FROM`, `SUPPORTED_BY`) are permitted between C-MAPSS machines and MVTec inspection artifacts.
- **No Shared Synthetic Health Scores**: Visual anomaly scores do not alter C-MAPSS Remaining Useful Life (RUL) or Health Index calculations.

---

## 2. Evidence Object Abstraction

All operational observations, mathematical transformations, model predictions, decisions, alerts, and benchmark truths are unified behind the generalized `EvidenceRecord` abstraction.

### Core Attributes
- `id` (UUID): Immutable primary identifier.
- `domain` (`MACHINE_HEALTH` | `VISUAL_INSPECTION`): Strict domain boundary.
- `entity_type` (`MACHINE`, `PREDICTION`, `RISK_ASSESSMENT`, `ALERT`, `INSPECTION_RUN`, `INSPECTION_RESULT`): Primary entity class.
- `entity_id` (String): Authoritative business/foreign key identifier.
- `evidence_type` (`TELEMETRY`, `FEATURE`, `RUL_PREDICTION`, `HEALTH_INDEX`, `RISK_ASSESSMENT`, `RISK_REASON`, `ALERT`, `IMAGE`, `ANOMALY_SCORE`, `INSPECTION_DECISION`, `LOCALIZATION`, `GROUND_TRUTH`, `ANALYTICS`, `MODEL_ARTIFACT`, `DATASET_PROVENANCE`).
- `source`: Database table or source store (e.g., `telemetry_records`, `inspection_results`).
- `source_reference`: Traceable query pointer (e.g., `machine_id=TURBOFAN-ENG-001,cycle=192`).
- `observation_cycle`: Telemetry sequence counter (preserved for C-MAPSS; null for visual).
- `observation_time`: UTC observation timestamp (preserved for visual; null for telemetry cycles without wall-clock timestamps).
- `value`: Typed, structured JSON payload (strictly preserving units and dimensions).
- `unit`: Measurement unit (e.g., `cycles`, `distance`, `psia`, `°R`).
- `confidence`: Calibrated statistical confidence (null unless genuine calibrated confidence exists).
- `quality_state` (`VERIFIED`, `DERIVED`, `BENCHMARK_GROUND_TRUTH`, `PROVENANCE_ONLY`, `UNAVAILABLE`).
- `explanation`: Deterministic human-readable explanation derived directly from persisted values.
- `provenance`: Detailed dictionary capturing software versions, model versions, feature configurations, and dataset references.

---

## 3. High-Level Evidence Flow

```
                      +---------------------------------------+
                      |       EVIDENCE INTELLIGENCE LAYER     |
                      |              (Unified API)            |
                      +-------------------+-------------------+
                                          |
                +-------------------------+-------------------------+
                |                                                   |
      [ DOMAIN A: MACHINE_HEALTH ]                        [ DOMAIN B: VISUAL_INSPECTION ]
      (NASA C-MAPSS FD001)                                (MVTec AD metal_nut)
                |                                                   |
    +-----------v-----------+                           +-----------v-----------+
    | Telemetry Observation |                           |   Raw Source Image    |
    +-----------+-----------+                           +-----------+-----------+
                | DERIVED_FROM                                      | PRODUCED_BY
    +-----------v-----------+                           +-----------v-----------+
    | Causal Feature Vector |                           |  PatchCore Embedding  |
    +-----------+-----------+                           +-----------+-----------+
                | DERIVED_FROM                                      | DERIVED_FROM
    +-----------v-----------+                           +-----------v-----------+
    |    RUL Prediction     |                           | Anomaly Score & Decision|
    +-----------+-----------+                           +-----------+-----------+
                | DERIVED_FROM                                      | HAS_ARTIFACT / EVALUATED_AGAINST
    +-----------v-----------+                           +-----------v-----------+
    | Deterministic Risk    |                           | Localization Heatmap  |
    +-----------+-----------+                           | Benchmark Ground Truth|
                | TRIGGERED                             +-----------------------+
    +-----------v-----------+
    |   Operational Alert   |
    +-----------------------+

                      =========================================
                      X  CROSS-DOMAIN RELATIONSHIPS REJECTED  X
                      =========================================
```

---

## 4. Key Subsystems

1. **Lightweight Relational Evidence Graph**:
   - Directed relationship model stored directly in PostgreSQL (`evidence_relationships`).
   - Relationship types: `DERIVED_FROM`, `SUPPORTED_BY`, `PRODUCED_BY`, `EVALUATED_AGAINST`, `TRIGGERED`, `BELONGS_TO`, `HAS_ARTIFACT`, `HAS_PROVENANCE`.
   - Domain isolation validation on creation: raises `CrossDomainEvidenceException` (HTTP 400) if source and target records belong to different domains.

2. **Evidence Bundles**:
   - Organized collections of evidence records representing a complete investigation or audit context (`evidence_bundles`, `evidence_bundle_items`).
   - Machine Health Bundle: latest telemetry cycle, causal feature vector, RUL prediction, Health Index, deterministic risk assessment, reason codes, active alerts, and model provenance.
   - Visual Inspection Bundle: source image reference, PatchCore memory bank version, anomaly score, process decision, localization heatmap, and benchmark ground truth mask.

3. **Deterministic Materialization**:
   - `backend/scripts/materialize_evidence.py` scans existing persisted records from M4, M5, M6, and M7.
   - 100% idempotent: subsequent executions perform zero insertions and generate zero duplicate records.
