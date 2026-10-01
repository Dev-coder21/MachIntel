# MachIntel Dataset Decision Document

**Status:** Approved (Phase 0 Milestone M0 Gate)  
**Author:** MachIntel Engineering Core  
**Review Standard:** MachIntel Master Implementation Document (Section 4 & Section 27)  

---

## 1. Executive Summary

MachIntel is an industrial machine-health intelligence and visual inspection platform designed to operate with uncompromising scientific integrity. In accordance with the MachIntel Master Implementation Document:
- We build real functionality, not mock or synthetic demo paths.
- We utilize authentic, publicly available benchmark datasets with documented provenance.
- We strictly adhere to the **Critical Dataset Rule**: we never imply that unrelated industrial inspection images and turbofan telemetry belong to the same machine.
- We reject premature or fraudulent claims of "multimodal fusion" where datasets lack a physical, temporal, or causal shared entity.

Following a comprehensive evaluation of candidate industrial datasets across 15 rigorous criteria, the following foundational selections are locked for Phase 1 through Phase 16:

1. **Primary Telemetry Dataset:** **NASA C-MAPSS (Commercial Modular Aero-Propulsion System Simulation) — Subset FD001**
   - *Domain:* Gas turbine turbofan engine degradation telemetry.
   - *Key Strengths:* 100 run-to-failure engines in train set, 100 partially degraded test engines, explicit operational cycles, zero missing values, canonical entity-preserving train/test splits, official ground truth Remaining Useful Life (RUL) vector, and high relevance to real predictive maintenance operations.
2. **Primary Computer Vision Dataset:** **MVTec Anomaly Detection (MVTec AD) — Focused on Industrial Component Inspection (`metal_nut` as primary vertical, extensible to full 15 classes)**
   - *Domain:* Industrial visual surface inspection and defect localization.
   - *Key Strengths:* High-resolution images (700×700 to 1024×1024), pixel-level ground truth masks for all defects, realistic unsupervised anomaly detection formulation (train on defect-free parts only, test on defect and normal parts), clear industry-standard metrics (AUROC and PRO), and manageable local compute footprint.

All alternative datasets (MVTec AD 2, MVTec 3D-AD, AI4I 2020 Predictive Maintenance, IMS Bearing, and MetroPT-3) have been rigorously evaluated and formally rejected for the initial production milestone. Their evaluation profiles and rejection justifications are documented in detail below.

---

## 2. Comprehensive Candidate Evaluation Matrix

The table below summarizes the multi-criteria evaluation of all 7 evaluated candidate datasets against MachIntel's 15 validation dimensions.

| # | Dimension | NASA C-MAPSS (FD001) | MVTec AD | MVTec AD 2 / LOCO AD | MVTec 3D-AD | AI4I 2020 Predictive Maintenance | IMS Bearing Dataset | MetroPT-3 |
|---|---|---|---|---|---|---|---|
| **1** | **Official Source** | NASA Prognostics Center of Excellence (PCoE) | MVTec Software GmbH (CVPR 2019 / IJCV 2021) | MVTec Software GmbH (CVPR 2025 / WACV 2022) | MVTec Software GmbH (3DV 2022) | UCI Machine Learning Repository | NASA PCoE / University of Cincinnati | UCI Machine Learning Repository |
| **2** | **License / Usage** | Public Domain (NASA Open Data) | CC BY-NC-SA 4.0 (Non-commercial research) | CC BY-NC-SA 4.0 | CC BY-NC-SA 4.0 | CC BY 4.0 | Public Domain | CC BY 4.0 |
| **3** | **Dataset Size** | 20,631 train rows, 13,096 test rows (FD001: 100 train / 100 test units) | 5,354 images (metal_nut: 220 train normal, 115 test defect, 22 test normal) | 8,000+ images (AD2) / 3,644 images (LOCO) | 4,147 3D scans + RGB (~14 GB) | 10,000 tabular records | 3 run-to-failure tests (~several GBs vibration ASCII) | ~14 million sensor readings (4 months, 1Hz) |
| **4** | **Entities / Machine IDs** | 100 distinct train engines (`unit_number` 1–100), 100 test engines | Categorical parts (`metal_nut`, `cable`, etc.); independent part instances | Categorical parts; independent part instances | Categorical parts; 3D scanned instances | Synthetic product IDs (`L/M/H` variants); no physical machine life cycles | 4 physical bearings on 1 test rig across 3 test runs | 1 physical metro compressor unit (APU) on Train 04 |
| **5** | **Available Timestamps** | Sequential operational cycles (`time_in_cycles` 1 to $T_{fail}$) | Static inspection capture timestamps (non-temporal) | Static inspection capture timestamps | Static 3D capture timestamps | Arbitrary synthetic sequence index; no true timestamps | Continuous high-frequency time stamps (20 kHz sampling every 10 min) | Continuous 1 Hz ISO 8601 timestamps (2020-02 to 2020-06) |
| **6** | **Available Labels** | Operational cycle, run-to-failure endpoint ($RUL=0$), test RUL vector | Image-level binary (normal/defect), defect type, pixel-level binary mask | Structural vs logical anomaly labels, bounding boxes, masks | 3D point cloud anomaly labels, 2D masks | Binary `Machine failure`, 5 failure modes (TWF, HDF, PWF, OSF, RNF) | Implicit bearing failure at end of test; no explicit intermediate annotations | Rare failure events (air leaks, compressor cutoffs) logged manually |
| **7** | **Target Prediction Task** | Remaining Useful Life (RUL) regression & Health Index degradation | Unsupervised anomaly detection & pixel defect localization | Structural + logical anomaly detection & localization | 3D surface defect detection & depth anomaly segmentation | Tabular multi-class or binary failure classification | Anomaly detection / degradation trend tracking via vibration spectrum | Time-series anomaly detection / failure event prediction |
| **8** | **Missingness** | 0.0% (Clean simulation outputs) | 0.0% (Curated image files, zero corruptions) | 0.0% | 0.0% | 0.0% (Synthetic tabular) | Negligible missingness; large file corruption risk | Moderate missingness, sensor dropouts, GPS/bus disconnects |
| **9** | **Class Imbalance** | Continuous trajectory; healthy cycles dominate early; balanced units | Train: 100% normal. Test: ~80% defective, ~20% normal | Train: 100% normal. Test: balanced structural/logical defects | Train: 100% normal. Test: variable defect ratios | Severe: 339 failures out of 10,000 (3.39% positive class) | N=3 failure endpoints across hundreds of gigabytes | Severe: <0.1% failure cycles across 14 million rows |
| **10** | **Temporal Ordering** | Yes. Strict sequential cycle progression per engine unit. | No. Independent part instances on an inspection line. | No. Independent instances. | No. Independent instances. | Weak/Synthetic. Row order does not reflect continuous physical wear. | Yes. High-speed vibration signal over 30 days. | Yes. 1 Hz continuous time series. |
| **11** | **Entity-Aware Splitting** | Yes. Clean partition by engine `unit_number` (zero leakage). | Yes. Category-based and instance-based partitioning. | Yes. Set split into local public vs remote private benchmark. | Yes. Category-based partition. | No. Random row splits leak synthetic generation artifacts. | Severely constrained. N=3 runs means train on 2, test on 1. | No. Single asset time split susceptible to seasonal/operational shifts. |
| **12** | **Product Workflow Fit** | **Exceptional.** Natural fit for fleet telemetry, RUL estimation, and health tracking. | **Exceptional.** Direct industrial inspection station workflow with visual defect masks. | High, but excessive complexity for baseline inspection station. | Medium. Requires 3D rendering and point-cloud viewing stack. | Low. Toy tabular dataset, does not represent a real continuous telemetry pipeline. | Low. Raw vibration signal requires dedicated signal-processing microservice. | Medium. High operational noise, unwieldy for reproducible local testing. |
| **13** | **Recommended Baseline** | Ridge Regression / Random Forest with rolling sensor statistics; linear RUL target | Pre-trained CNN/ViT patch embeddings + kNN/PatchCore or Mahalanobis distance | Multi-scale structural memory bank + logical rule validator | 3D patch memory bank + depth autoencoder | Random Forest / XGBoost classifier | FFT spectral peak tracking + Isolation Forest | Autoencoder / Rolling Mahalanobis distance |
| **14** | **Important Limitations** | Modelled simulation (MAPSS physics), not physical flight data; discrete cycles. | Static parts under controlled lighting; no physical link to turbofan engines. | Complex evaluation protocol (requires benchmark server for official test set). | Heavy compute/memory footprint (~14 GB download); complex 3D preprocessing. | Tabular synthetic records without true temporal degradation dynamics. | Extremely small sample size (n=3 test runs); sensor drift vs actual failure ambiguous. | Messy uncurated real data; noisy manual maintenance logs; single asset instance. |
| **15** | **Multimodal Fusion Feasibility** | **None with MVTec.** Completely distinct physics, entities, and timescales. | **None with C-MAPSS.** Completely distinct domain. | None with C-MAPSS. | None with C-MAPSS. | None with MVTec. | None with MVTec. | None with MVTec. |

---

## 3. Deep-Dive Candidate Profiles & Decision Rationale

### 3.1 Primary Telemetry Selection: NASA C-MAPSS (FD001)

#### Selection Justification
NASA C-MAPSS (Commercial Modular Aero-Propulsion System Simulation) is the premier benchmark in prognostic health management (PHM). Subset **FD001** simulates high-bypass turbofan engines under sea-level operating conditions with a single failure mode: High-Pressure Compressor (HPC) degradation.

- **Entity Integrity:** Contains 100 distinct engine units in the training set and 100 distinct engine units in the test set. Each engine begins with varying initial wear and operates until complete functional failure (in train) or until a censored observation cycle (in test).
- **Leakage Prevention:** By splitting at the engine unit level (`unit_number`), we eliminate entity leakage. Furthermore, time-series windows respect cycle progression, strictly preventing temporal look-ahead leakage.
- **Deterministic Evaluation:** NASA provides an official ground truth vector (`RUL_FD001.txt`) containing the exact remaining operational cycles for every test engine at its last recorded cycle. This enables mathematically rigorous evaluation using Root Mean Squared Error (RMSE) and the official NASA asymmetric scoring function.
- **Zero Missingness:** Provides 21 sensor channels and 3 operational settings with 100% integrity, allowing the engineering team to focus on robust feature engineering (rolling means, standard deviations, degradation trends) rather than imputing missing records.

#### Operational Product Workflow
In MachIntel, C-MAPSS engines are mapped directly to the **Machine Registry**:
- Each engine is registered as an industrial gas turbine asset (e.g., `TURBOFAN-ENG-001` through `TURBOFAN-ENG-100`).
- The telemetry ingestion pipeline streams cycle records into `telemetry_records`.
- The Machine Health ML service computes rolling feature windows, predicts Remaining Useful Life (RUL), and generates a normalized Health Index $HI(t) \in [0.0, 1.0]$.
- When $HI(t)$ degrades below operational thresholds, the risk engine triggers explainable alerts (e.g., `CRITICAL_RUL_THRESHOLD_BREACHED`).

---

### 3.2 Primary Visual Inspection Selection: MVTec AD (`metal_nut`)

#### Selection Justification
The MVTec Anomaly Detection (MVTec AD) benchmark is the de facto gold standard for industrial computer vision inspection. It contains 5,354 real-world high-resolution images across 15 categories (10 rigid/flexible objects and 5 textures).

For MachIntel's primary inspection vertical, we lock the **`metal_nut`** category (220 normal training images, 115 defective test images spanning 4 authentic manufacturing failure modes: `bent`, `color`, `flip`, and `scratch`, plus 22 normal test images). The underlying architecture is engineered to be fully category-agnostic and seamlessly extensible to all 15 categories.

- **Industrial Fidelity:** Images represent realistic manufacturing camera setups with controlled lighting and industrial defects.
- **Ground Truth Localization:** Defect images come with pixel-accurate ground-truth binary masks, enabling both image-level anomaly detection and pixel-level defect localization/segmentation.
- **Unsupervised Paradigm:** In real manufacturing, defective parts are rare and defects are unpredictable. MVTec AD models the true industrial scenario: models train strictly on defect-free parts (`good`), learning nominal feature distributions, and must flag any anomalous deviation at test time.
- **Compute Efficiency:** The dataset is easily hosted locally on development workstations and MacBook environments, running inference swiftly without requiring multi-GPU cloud clusters.

#### Operational Product Workflow
In MachIntel, visual inspection operates through the **Visual Inspection Station**:
- An operator or automated camera uploads high-resolution component imagery.
- The CV pipeline validates MIME type, dimensions, and image integrity.
- The model extracts spatial feature embeddings, computes an anomaly distance score, and generates a defect localization heatmap and binary segmentation overlay.
- Inspection records, anomaly scores, defect classifications, and visual overlay artifacts are permanently stored with model version provenance.

---

### 3.3 Rejected Telemetry Alternatives

#### 1. AI4I 2020 Predictive Maintenance Dataset
- **Official Source:** UCI Machine Learning Repository (Stephan Matzka, 2020).
- **License:** CC BY 4.0.
- **Why Evaluated:** Synthetic 10,000-record dataset designed to reflect CNC milling machines, with temperatures, torque, speed, and tool wear.
- **Reason for Rejection:** 
  1. The dataset consists of independent tabular rows generated via synthetic rules. It does not provide continuous, sequential time-series tracking of distinct machine entities over their operational life cycles.
  2. Machine wear is represented by an artificial linear counter (`Tool wear [min]`) rather than real sensor dynamics.
  3. Splitting rows randomly creates artificial data leakage, while grouping by product variant fails to model temporal degradation. It cannot support a realistic streaming telemetry pipeline.

#### 2. IMS Bearing Dataset
- **Official Source:** NASA Prognostics Center of Excellence / University of Cincinnati (J. Lee et al., 2007).
- **License:** Public Domain.
- **Why Evaluated:** Real-world physical test bench with 4 Rexnord bearings run to failure under constant load at 2,000 RPM, recording 20 kHz vibration data.
- **Reason for Rejection:**
  1. Contains only **three test runs** ($N=3$). In an engineering product, having only 3 machine instances makes it statistically impossible to perform proper entity-aware cross-validation and independent test evaluation without severe overfitting or zero generalization power.
  2. The raw files are multi-gigabyte ASCII dumps of raw 20 kHz acceleration signals. Ingesting and processing this on a local development machine requires a massive dedicated signal-processing ETL pipeline (STFT/FFT/wavelets) that distracts from the core platform architecture.

#### 3. MetroPT-3 Dataset
- **Official Source:** UCI Machine Learning Repository (Metro do Porto compressor APU).
- **License:** CC BY 4.0.
- **Why Evaluated:** Real-world continuous telemetry from an air production unit on an operating passenger train over 4 months.
- **Reason for Rejection:**
  1. Contains only a **single physical train unit** (Train 04), precluding multi-machine fleet analytics.
  2. Failure events are extremely sparse and inconsistently logged by human operators, making objective benchmark evaluation and reproducible automated testing unreliable.
  3. High noise floor and frequent network dropouts create excessive data-cleaning overhead without yielding clean prognostic signals.

---

### 3.4 Rejected Visual Inspection Alternatives

#### 1. MVTec AD 2 / MVTec LOCO AD
- **Official Source:** MVTec Software GmbH (Heckler-Kram et al., CVPR 2025; Bergmann et al., WACV 2022).
- **License:** CC BY-NC-SA 4.0.
- **Why Evaluated:** Next-generation industrial anomaly benchmark focusing on complex structural and logical constraint anomalies.
- **Reason for Rejection:**
  1. Official evaluation requires submitting test predictions to MVTec's remote Benchmark Server for the private test partition; it is not self-contained for offline, local, automated test suites.
  2. Introduces domain-shift and complex logical rules (e.g., missing items in a kit) that require multi-object relational reasoning, significantly increasing baseline complexity without changing the underlying architecture of an inspection platform.
  3. Deferred to Phase 14 / future research roadmap.

#### 2. MVTec 3D-AD
- **Official Source:** MVTec Software GmbH (3DV 2022).
- **License:** CC BY-NC-SA 4.0.
- **Why Evaluated:** Combines high-resolution 2D RGB photography with 3D industrial sensor point clouds and depth maps.
- **Reason for Rejection:**
  1. Exceeds 14 GB of storage, creating substantial local development hurdles on standard workstations.
  2. Requires specialized 3D point-cloud processing libraries (Open3D, PointNet++) and heavy GPU memory bandwidth.
  3. Most industrial visual inspection stations in commercial operation rely on 2D optical cameras; adding 3D point clouds at Milestone M0 adds substantial infrastructure overhead without validating the core product workflows.

---

## 4. Final Dataset Decision Summary Table

| Category | Role | Selected Dataset | Primary Subset / Focus | Provenance & License |
|---|---|---|---|---|
| **Machine Telemetry** | Primary Ground Truth | **NASA C-MAPSS** | FD001 (100 train / 100 test turbofan engines) | NASA PCoE / Open Data (Public Domain) |
| **Visual Inspection** | Primary Ground Truth | **MVTec AD** | `metal_nut` (extensible to all 15 classes) | MVTec Software GmbH (CC BY-NC-SA 4.0) |
| **Multimodal Intelligence** | Synthesis Architecture | **Evidence-Layer Aggregation** | Independent evidence streams unified at Risk & Investigation Layer | MachIntel System Architecture (No synthetic cross-modal coupling) |

---

## 5. Next Steps

With Milestone M0 dataset selection locked:
1. Complete Dataset Cards adhering to ML documentation standards (`dataset-cards.md`).
2. Document rigorous entity-aware splitting and leakage prevention rules (`split-strategy.md`).
3. Formalize the mathematical formulation and baseline models for RUL regression and visual anomaly localization (`task-selection.md`).
4. Detail the Evidence Layer architecture and define clear boundaries prohibiting fraudulent multimodal fusion (`multimodal-feasibility.md`).
