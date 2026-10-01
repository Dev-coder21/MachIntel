# MachIntel Split Strategy & Leakage Prevention Protocol

**Document Version:** 1.0 (Phase 0 Validation Sprint)  
**Maintained By:** MachIntel Engineering Core  
**Review Standard:** Section 4.2 & Section 6.3 of MachIntel Master Blueprint  

---

## 1. Principles of Industrial Data Splitting

Machine health forecasting and computer vision inspection require rigorous split protocols. Naive splitting strategies (such as random row shuffling) introduce catastrophic **data leakage**, resulting in artificially inflated model accuracy that collapses in production.

MachIntel establishes four unbreakable splitting laws:
1. **The Entity Boundary Law:** No physical machine entity (or simulated engine unit) may ever have its operational cycles split across both training and evaluation sets.
2. **The Temporal Arrow Law:** In time-series telemetry, future sensor readings must never be accessible during feature extraction, normalization, or prediction for an earlier cycle.
3. **The Unsupervised Isolation Law:** In visual anomaly inspection, no defective samples, defect masks, or test-set normal images may ever participate in feature representation fitting or memory bank creation.
4. **The Preprocessing Isolation Law:** All statistical transformers (scalers, imputers, PCA projections, rolling standardizations) must be fit strictly on training splits and applied deterministically to validation and test splits.

---

## 2. Machine Health Telemetry Split: NASA C-MAPSS (FD001)

### 2.1 The Failure of Random Row Splitting
In sequential run-to-failure telemetry, each row represents an operational cycle $t$ for engine $i$. Consecutive cycles ($t$ and $t+1$) have near-identical operational settings and sensor values ($r > 0.98$). 

If rows are shuffled randomly:
- Cycle $t$ of Engine 12 lands in the training set while cycle $t+1$ of Engine 12 lands in the test set.
- The model memorizes the specific degradation trajectory of Engine 12 rather than learning generalizable degradation dynamics.
- The test score reflects random interpolation rather than true prognostic forecasting.

### 2.2 Canonical Entity-Level Partitioning Strategy
MachIntel enforces strict **Entity-Level Partitioning** across the 100 training units and 100 test units:

```
NASA C-MAPSS FD001 Total Dataset (200 Engines)
├── Training & Internal Validation Pool (train_FD001.txt - 100 Run-to-Failure Engines)
│   ├── Internal Training Partition (Units 1 to 80 - 80 Engines, ~16,400 cycles)
│   │   └── Used for fitting normalizers, feature scalers, and ML model weights
│   └── Internal Validation Partition (Units 81 to 100 - 20 Engines, ~4,231 cycles)
│       └── Used for hyperparameter tuning, window size optimization, and early stopping
└── Benchmark Test Set (test_FD001.txt - 100 Censored Engines, 13,096 cycles)
    └── Evaluated at censored cycle T_obs against official ground truth vector RUL_FD001.txt
```

### 2.3 Censoring & Test Evaluation Protocol
- **Training Trajectories:** Complete run-to-failure trajectories where the final observed cycle represents engine failure ($RUL = 0$).
- **Test Trajectories:** Operational cycles are truncated (censored) at an arbitrary operating cycle $T_{obs}$ before failure.
- **Evaluation Point:** Predictions are evaluated at the final cycle $T_{obs}$ for each of the 100 test engines. The predicted remaining life $\widehat{RUL}_i(T_{obs})$ is evaluated directly against the NASA ground-truth value $RUL_i \in \text{RUL\_FD001.txt}$.

### 2.4 Preprocessing & Scaling Rules
```python
# PREPROCESSING ISOLATION PROTOCOL
from sklearn.preprocessing import MinMaxScaler

# 1. Fit scaler ONLY on Internal Training Partition (Units 1-80)
train_mask = df_train["unit_number"] <= 80
scaler = MinMaxScaler(feature_range=(-1, 1))
scaler.fit(df_train.loc[train_mask, active_sensors])

# 2. Transform validation and test sets using the fitted scaler
df_train.loc[~train_mask, active_sensors] = scaler.transform(df_train.loc[~train_mask, active_sensors])
df_test[active_sensors] = scaler.transform(df_test[active_sensors])
```

---

## 3. Industrial Computer Vision Split: MVTec AD (`metal_nut`)

### 3.1 Unsupervised Anomaly Detection Protocol
In real industrial manufacturing lines:
- Over 99% of manufactured parts coming off a stamping or CNC line are defect-free.
- Defects are rare, uncataloged, and structurally diverse (e.g. unexpected burrs, discoloration, hairline cracks).
- Supervised binary classification fails because classifiers overfit to the few specific defect types seen in training.

Therefore, MachIntel adheres to MVTec AD's **Unsupervised Anomaly Detection Protocol**:
- The model trains exclusively on nominal, defect-free parts (`good`).
- At inference time, the model must flag any deviation from nominal appearance as an anomaly and localize the anomalous pixels.

### 3.2 Partition Breakdown (`metal_nut`)

```
MVTec AD metal_nut (357 Total Images)
├── Nominal Training Pool (train/good/ - 220 Images)
│   ├── Model Representation Partition (180 Good Images)
│   │   └── Used for extracting normal patch feature embeddings & building memory bank
│   └── Calibration / Threshold Validation Partition (40 Good Images)
│       └── Held out to calibrate nominal anomaly score distribution and set alpha = 0.01 threshold
└── Official Test Evaluation Set (test/ - 137 Images)
    ├── Nominal Test Samples (test/good/ - 22 Images)
    └── Defective Test Samples with Ground Truth Masks (115 Images)
        ├── Bent Flange/Threads (25 Images + 25 Masks)
        ├── Color / Oxidation (25 Images + 25 Masks)
        ├── Inverted / Flip Assembly (24 Images + 24 Masks)
        └── Surface Scratch / Burr (41 Images + 41 Masks)
```

### 3.3 Leakage Prevention in Representation Learning
- **Zero Defect Exposure:** Neither defect images nor defect masks are ever seen during feature extraction or memory bank creation.
- **Backbone Freezing:** When using pre-trained vision backbones (e.g., WideResNet-50 or EfficientNet-B4 pre-trained on ImageNet), backbone weights remain frozen to eliminate label leakage from external datasets.
- **Independent Thresholding:** The anomaly decision threshold $\tau$ is calibrated using only the 40 held-out nominal validation images (setting $\tau$ to the 99th percentile of nominal scores, guaranteeing an operating False Alarm Rate $\le 1\%$) before testing on the 137 test samples.

---

## 4. Summary of Split Specifications

| Metric / Parameter | Machine Health Telemetry (C-MAPSS FD001) | Computer Vision Inspection (MVTec AD metal_nut) |
|---|---|---|
| **Split Unit** | Engine `unit_number` | Image instance + Category |
| **Train Set Size** | 80 engine units (~16,400 cycles) | 180 normal images (`good`) |
| **Validation Set Size** | 20 engine units (~4,231 cycles) | 40 normal images (`good`) |
| **Test Set Size** | 100 censored engine units (13,096 cycles) | 137 images (22 good, 115 defects) |
| **Defect Masks in Train** | None (N/A) | Strictly 0 |
| **Leakage Protections** | Entity-isolated; scalers fit on train only; temporal rolling windows | Frozen backbone; zero defect images in train; independent threshold calibration |
| **Evaluation Criterion** | RMSE and NASA Score at final cycle $T_{obs}$ | Image AUROC, Pixel AUROC, and PRO score |
