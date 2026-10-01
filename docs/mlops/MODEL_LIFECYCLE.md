# MachIntel MLOps & Model Lifecycle Architecture (Milestone M14)

## 1. Overview & Core Principles

MachIntel employs a **defensible, local-first model lifecycle** engineered specifically for safety-critical industrial decision support. The architecture provides full reproducibility, cryptographic integrity verification, auditable lifecycle transitions, and deterministic promotion gates without relying on cloud platforms, external model registries, or autonomous retraining loops.

### Non-Negotiable Tenets
1. **Local-First Authoritative Metadata**: PostgreSQL stores authoritative registry metadata, lifecycle states, promotion records, and immutable evaluation manifests.
2. **Local Filesystem Artifacts**: Machine learning binaries and feature configs reside locally under `storage/models/`.
3. **Cryptographic SHA-256 Verification**: Every model binary is integrity-checked against its recorded SHA-256 digest before inference and on administrative demand.
4. **Deterministic Promotion Gates**: Promotion requires passing 8 deterministic gates; no model can enter `PROMOTED` state without passing evaluation criteria.
5. **No Online Retraining**: Automated background retraining is strictly prohibited. Retraining workflows are explicit, offline, and human-in-the-loop.
6. **Domain Separation**: Machine Health (`MACHINE_HEALTH` — NASA C-MAPSS FD001) and Visual Inspection (`VISUAL_INSPECTION` — MVTec AD `metal_nut`) are strictly segregated evidence verticals.

---

## 2. Model Lifecycle States & State Machine

Every registered model transitions through well-defined lifecycle states:

```
[ REGISTERED ] ──(Evaluate)──> [ EVALUATED ] ──(Benchmark)──> [ CANDIDATE ]
       │                              │                             │
       │                              │ (Pass Deterministic Gates)  │
       ▼                              ▼                             ▼
  [ REJECTED ]                  [ PROMOTED ] <──────────────────────┘
                                      │
                         (Superseded / Decommissioned)
                                      ▼
                                 [ RETIRED ]
```

### Supported States
- **`REGISTERED`**: Artifact ingested, SHA-256 digest calculated, basic metadata stored. Not yet formally evaluated.
- **`EVALUATED`**: Evaluated on official split benchmark; evaluation manifest and metrics immutably recorded.
- **`CANDIDATE`**: Identified as a candidate for production serving.
- **`PROMOTED`**: Active serving model for its domain. Exactly one model per domain can be active in production.
- **`RETIRED`**: Previously promoted model superseded by a new release or explicitly retired.
- **`REJECTED`**: Model failed promotion gates or evaluation benchmarks.

### Permitted Transitions
- `REGISTERED` → `EVALUATED`, `REJECTED`
- `EVALUATED` → `CANDIDATE`, `PROMOTED`, `REJECTED`
- `CANDIDATE` → `PROMOTED`, `REJECTED`
- `PROMOTED` → `RETIRED`
- `RETIRED` → `CANDIDATE` (re-activation requires passing promotion gates again)

---

## 3. Registered Production Models & Verified Checksums

### RUL Machine Health Models (NASA C-MAPSS FD001)

#### 1. `rul-randomforest-v1.0.0` (ACTIVE PRODUCTION)
- **Domain**: `MACHINE_HEALTH`
- **Family**: `RUL_REGRESSION`
- **Algorithm**: `RandomForestRegressor` (scikit-learn)
- **Status**: `PROMOTED` (`is_active=True`)
- **Artifact Directory**: `storage/models/rul/rul-randomforest-v1.0.0/`
- **Primary Binary**: `model.joblib`
- **SHA-256**: `186cda72751d0cfbe3408968b6682e65b993d7fd972646bce0c914e999571b1b`
- **Artifact Size**: `17,435,969 bytes` (~16.63 MB)
- **Scaler Binary**: `scaler.joblib` (SHA-256: `f3811779e7f703c52dd5de467e41dac2181041fd6cb18336d15bda8cbd141aed`)
- **Dataset**: `NASA C-MAPSS FD001` (Units 1–80 training, Units 81–100 validation, official test)
- **Features**: 17 active sensor channels, 102 rolling statistical features (window=20)
- **Target**: $RUL^* = \min(125, T_{fail} - t)$
- **Validation RMSE**: `19.5411` (Selection criterion: Lowest internal validation RMSE)
- **Official Test RMSE**: `19.0187`

#### 2. `rul-ridge-v1.0.0` (BENCHMARK CANDIDATE)
- **Domain**: `MACHINE_HEALTH`
- **Family**: `RUL_REGRESSION`
- **Algorithm**: `Ridge` (scikit-learn)
- **Status**: `EVALUATED` (`is_active=False`)
- **Artifact Directory**: `storage/models/rul/rul-ridge-v1.0.0/`
- **Primary Binary**: `model.joblib`
- **SHA-256**: `6eacb3d910542fe2e3349cd0451a22428aa58d6af2240d4a82fbf15ed96946bf`
- **Artifact Size**: `1,369 bytes`
- **Validation RMSE**: `21.2868`
- **Official Test RMSE**: `18.5714` (Note: RF selected for production due to lower internal validation RMSE)

### Computer Vision Anomaly Detection Model (MVTec AD metal_nut)

#### 3. `mvtec-patchcore-metalnut-v1.0.0` (ACTIVE PRODUCTION)
- **Domain**: `VISUAL_INSPECTION`
- **Family**: `ANOMALY_DETECTION`
- **Algorithm**: `PatchCore` with frozen `Wide_ResNet50_2` (PyTorch)
- **Status**: `PROMOTED` (`is_active=True`)
- **Artifact Directory**: `storage/models/cv/mvtec-patchcore-metalnut-v1.0.0/`
- **Primary Binary**: `memory_bank.pt`
- **SHA-256**: `e63181c3b44a541861a30b375800e08169fcd7fd0205f464ad3596fe21f60d90`
- **Artifact Size**: `52,987,461 bytes` (~50.53 MB)
- **Dataset**: `MVTec AD` (`metal_nut` category)
- **Training Set**: 220 normal images
- **Test Set**: 115 official test images (normal + defects: bent, color, flip, scratch, thread)
- **Feature Backbone**: Layers 2 and 3, feature dimension 1536
- **Patch Grid**: 28x28 (784 patches/image, 172,480 total patches)
- **Coreset Reduction**: 5% subsample (8,624 coreset patches, random seed 42)
- **Decision Threshold**: $\tau = 2.8155$ (3-sigma threshold fitted strictly on training normals)
- **Verified Metrics**:
  - Image ROC-AUC: `0.9858`
  - PR-AUC: `0.9967`
  - Precision: `0.9886`
  - Recall: `0.9355`
  - F1-Score: `0.9613`
  - Pixel ROC-AUC: `0.9769`

---

## 4. Deterministic Promotion Policy

Before any model can be promoted to `PROMOTED` state, the `ModelLifecycleService.evaluate_promotion_gates()` evaluates 8 deterministic gates:

| Gate | Name | Requirement |
|---|---|---|
| **GATE 1** | `GATE_1_ARTIFACT_EXISTS` | Artifact directory and primary binary exist on local filesystem. |
| **GATE 2** | `GATE_2_CHECKSUM_VALID` | Computed SHA-256 matches the recorded database digest. |
| **GATE 3** | `GATE_3_DATASET_VALID` | Linked dataset identifier matches an authorized dataset repository. |
| **GATE 4** | `GATE_4_FEATURE_CONFIG_VALID` | Feature engineering version and config references are registered. |
| **GATE 5** | `GATE_5_EVALUATION_MANIFEST_EXISTS`| Complete reproducibility training and evaluation manifests exist. |
| **GATE 6** | `GATE_6_REQUIRED_METRICS_PRESENT` | Required metrics are present (`val_rmse`/`test_rmse` for RUL; `roc_auc`/`f1_score` for CV). |
| **GATE 7** | `GATE_7_EVALUATION_PASSED` | Latest formal evaluation record status is `PASSED`. |
| **GATE 8** | `GATE_8_DOMAIN_ROLE_CONSISTENT` | Domain and family are consistent (`MACHINE_HEALTH` or `VISUAL_INSPECTION`). |

When a candidate model passes all gates and is promoted:
1. The currently active model in that domain is automatically transitioned to `RETIRED` (`is_active=False`).
2. The candidate model is transitioned to `PROMOTED` (`is_active=True`).
3. An immutable audit record is created in `model_promotions` capturing the user ID, timestamp, transition, and reason.

---

## 5. Inference Resolution & Fail-Safe Architecture

Production inference services do not load unmanaged file paths:
1. `PredictionService` calls `ModelLifecycleService.get_active_model(db, domain="MACHINE_HEALTH")`.
2. `VisualInspectionEndpoint` calls `ModelLifecycleService.get_active_model(db, domain="VISUAL_INSPECTION")`.
3. `get_active_model` verifies the artifact's SHA-256 checksum against disk before returning.
4. If the artifact is missing or corrupted, a `500 Internal Server Error` is raised. The system **never** fabricates a prediction or falls back to an unverified model.

---

## 6. Background Verification & Worker Integration

The worker infrastructure (Phase 12) includes the `MODEL_INTEGRITY_CHECK` job type:
- **Handler**: `handle_model_integrity_check(db, payload)`
- **Behavior**: Scans registered models, verifies file existence and SHA-256 digests.
- **Safety**: Purely diagnostic; does not alter production status automatically.

---

## 7. Operational Admin UI (`/admin/models`)

The frontend console provides full visibility into the model lifecycle:
- **Top KPI Ribbon**: Active RUL Model, Active Vision Model, Registered Artifacts, Deterministic Gate Policy.
- **Model Table**: Domain filter tabs, status badges, active indicators, truncated SHA-256 hashes, file sizes.
- **Detail Drawer**: Dataset & Feature Lineage, Reproducibility Manifests, Evaluation Records, Gate Validation Checklist, Cryptographic Verification, Promotion/Retirement Actions.
- **RBAC**: Read-only for `VIEWER` and `OPERATOR`. Promotion, retirement, and registration require `ADMIN` role.
