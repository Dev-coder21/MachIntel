# Source Lineage & Causal Tracing

## 1. Lineage Integrity

In **MachIntel**, every evidence record is directly grounded in authoritative persisted storage. Evidence is never synthesized, fabricated, or detached from origin records.

---

## 2. Domain A: Machine Health Lineage (C-MAPSS FD001)

The C-MAPSS lineage path preserves an unbroken causal chain from raw sensor measurements to fleet operations:

```
[1] Telemetry Observation (telemetry_records)
    • Ingestion from official NASA C-MAPSS FD001 text files.
    • Preserved observation cycle (1 to 192).
    • Operational settings (TRA, Mach) & 21 sensor values.
           │
           │ DERIVED_FROM (Rolling Window W=20, Strictly Causal)
           ▼
[2] Engineered Feature Vector (Causal ML Inputs)
    • Causal rolling mean, std, min, max, slope.
    • 7 invariant sensor channels strictly excluded.
    • Zero future lookahead leakage.
           │
           │ DERIVED_FROM
           ▼
[3] RUL Prediction (rul_predictions)
    • Linear Regression baseline (cmapss-rul-linear-v1.0.0).
    • Predicted remaining operational cycles.
           │
           │ DERIVED_FROM
           ▼
[4] Health Index & Deterministic Risk (risk_assessments)
    • Normalized continuous metric: HI ∈ [0.0, 1.0].
    • Deterministic piecewise risk evaluation (risk-policy-v1.0.0).
    • Reason codes generated: e.g. ["HEALTH_INDEX_CRITICAL", "RUL_BELOW_CRITICAL_THRESHOLD"].
           │
           │ TRIGGERED
           ▼
[5] Operational Alert (alerts)
    • Deterministic lifecycle: OPEN → ACKNOWLEDGED → RESOLVED.
    • Auditable operator attribution and lifecycle timestamps.
```

---

## 3. Domain B: Visual Inspection Lineage (MVTec AD metal_nut)

The MVTec visual inspection lineage path preserves an unbroken chain from raw optical capture to spatial localization:

```
[1] Raw Source Image (inspection_results)
    • Official test set optical capture (metal_nut category).
    • Path: data/raw/mvtec/metal_nut/test/{class}/{idx}.png.
           │
           │ PRODUCED_BY
           ▼
[2] PatchCore Embedding & Feature Memory Bank
    • Pretrained frozen WideResNet-50-2 backbone.
    • Aggregated patch tokens from layer2 (512d) and layer3 (1024d).
    • 5% random coreset subsampling (8,624 patch memory bank).
           │
           │ DERIVED_FROM
           ▼
[3] Anomaly Score & Decision (inspection_results)
    • Nearest-neighbor Euclidean distance score.
    • 3-sigma process threshold comparison (τ = 2.8155).
    • Deterministic PASS or DEFECT decision (cv-policy-v1.0.0).
           │
           ├── HAS_ARTIFACT
           ▼
[4] Anomaly Localization Heatmap
    • Bilinear interpolation to 224x224 RGB overlay.
    • Persisted PNG artifact: static/mvtec/artifacts/{run_id}/heatmap_{res_id}.png.
           │
           └── EVALUATED_AGAINST (Test Set Only)
           ▼
[5] Benchmark Ground Truth
    • Pixel-level ground truth mask and class label.
    • Strictly isolated from model during operational inference.
```
