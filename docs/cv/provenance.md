# Provenance, Versioning & Safety Constraints

## 1. Version Identifiers & Configuration Hierarchy

Every visual inspection execution maintains strict cryptographic and versioned provenance:

| Component | Identifier | Description |
| :--- | :--- | :--- |
| **Dataset** | `MVTec-AD-metal_nut` | Official MVTec AD fastener category snapshot |
| **Model** | `mvtec-patchcore-metalnut-v1.0.0` | Frozen WideResNet-50-2 PatchCore memory-bank model |
| **Feature Config** | `cv-feature-config-v1.0.0` | layer2 + layer3 upsample, avgpool(3x3), 784 patches x 1536d |
| **Policy** | `cv-policy-v1.0.0` | $\mu + 3\sigma$ normal calibration on 220 good train images |
| **Seed** | `42` | Deterministic random seed for coreset subsampling |

---

## 2. Artifact & Persistence Provenance

- **PostgreSQL Records**:
  - `dataset_metadata`: Tracks file checksums, source URLs, and category records.
  - `inspection_runs`: Immutable record created upon benchmark execution, documenting summary metrics, threshold, and parameter configuration.
  - `inspection_results`: Granular record per image linking source image, model score, PASS/DEFECT classification, benchmark ground truth, and storage paths.
- **Filesystem Artifacts**:
  - `storage/models/cv/mvtec-patchcore-metalnut-v1.0.0/memory_bank.pt`: Raw float32 tensor of coreset memory bank ($8,624 \times 1,536$).
  - `storage/models/cv/mvtec-patchcore-metalnut-v1.0.0/config.json`: Calibration statistics, threshold, and layer parameters.
  - `storage/inspections/{run_id}/heatmaps/`: Colormapped Jet visual heatmaps.
  - `storage/inspections/{run_id}/overlays/`: Alpha-blended visual overlays.

---

## 3. Reproducibility Notes

1. **Environment**:
   - Python: 3.13
   - PyTorch: 2.14.1
   - Torchvision: 0.29.1
   - Device: CPU / MPS (Apple Silicon compatible)
2. **Deterministic Seed**:
   PyTorch generator seed `42` is used for coreset subsampling. The resulting 8,624 patch indices are deterministic across identical framework versions.
3. **Execution Verification**:
   - Retraining and recalibrating the model via `python backend/scripts/train_cv_patchcore.py` reproduces the identical threshold $\tau = 2.8155$ and normal mean $\mu = 2.4895$.
   - Re-evaluating the official test split via `python backend/scripts/evaluate_cv_metalnut.py` reproduces the identical ROC-AUC $0.9858$ and category breakdown.

---

## 4. Safety & Operational Constraints

1. **No Failure Prediction / RUL Conflation**:
   Visual anomaly detection identifies optical surface deviation from nominal training reference. It does **not** predict remaining useful life, internal mechanical stress, or mechanical fracture.
2. **No Physical Safety Certification**:
   A `PASS` decision denotes the component has no detected optical surface anomalies exceeding the $3\sigma$ boundary. It does not certify structural airworthiness or metallurgical integrity.
3. **Domain Independence**:
   Visual inspection outputs are strictly decoupled from C-MAPSS engine telemetry and health indices.
