# Evidence Bundles

## 1. Bundle Concept

An **Evidence Bundle** groups related evidence records into an investigative package representing a specific asset assessment or inspection run.

Bundles enable engineers, operators, and compliance auditors to inspect the complete supporting evidence chain in a single unified view without executing multiple independent queries.

---

## 2. Bundle Structure

- `id` (UUID): Primary key.
- `bundle_name` (String): Descriptive human title (e.g. `Machine Health Bundle - TURBOFAN-ENG-001`).
- `domain` (`MACHINE_HEALTH` | `VISUAL_INSPECTION`): Strict domain boundary.
- `primary_entity_type` (String): The focal entity class (`MACHINE` or `INSPECTION_RUN`).
- `primary_entity_id` (String): The focal entity identifier.
- `description` (Text): Summary context of the bundle.
- `items` (List[EvidenceBundleItem]): Ordered proofs included in the bundle.
  - `evidence_id`: Foreign key reference to `evidence_records.id`.
  - `display_order`: Integer index for step-by-step presentation.
  - `role_in_bundle`: Functional role (e.g. `PRIMARY_OBSERVATION`, `CAUSAL_FEATURE`, `PREDICTION_INFERENCE`, `OPERATIONAL_DECISION`, `ARTIFACT_LOCALIZATION`, `BENCHMARK_EVALUATION`).

---

## 3. Bundle Types

### 3.1 Machine Health Evidence Bundle
- **Primary Entity**: `MACHINE` (`TURBOFAN-ENG-xxx`)
- **Included Evidence**:
  1. Latest Raw Telemetry Cycle (`TELEMETRY`)
  2. Causal Feature Vector (`FEATURE`)
  3. Predicted Remaining Useful Life (`RUL_PREDICTION`)
  4. Continuous Health Index (`HEALTH_INDEX`)
  5. Deterministic Risk State (`RISK_ASSESSMENT`)
  6. Explainable Reason Codes (`RISK_REASON`)
  7. Active Operational Alert (`ALERT`)

### 3.2 Visual Inspection Evidence Bundle
- **Primary Entity**: `INSPECTION_RUN` (MVTec AD `metal_nut` batch)
- **Included Evidence**:
  1. Optical Capture Reference (`IMAGE`)
  2. PatchCore Anomaly Distance (`ANOMALY_SCORE`)
  3. Threshold PASS/DEFECT Decision (`INSPECTION_DECISION`)
  4. Spatial Defect Localization Heatmap (`LOCALIZATION`)
  5. Benchmark Test Set Mask & Label (`GROUND_TRUTH`)
