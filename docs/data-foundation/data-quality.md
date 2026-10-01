# Data Quality & Validation Policy

## 1. Overview
In accordance with MachIntel core architectural principles, telemetry data ingested into PostgreSQL must be strictly verified against structural, logical, and physical data-quality constraints. Corrupted, duplicated, or synthesized data is rejected.

---

## 2. Validation Rules & Quality Checks

The ingestion validation engine (`backend.app.services.ingestion_service.DataQualityValidator`) runs the following automated validation checks prior to persistence:

| Check Name | Target Scope | Rule Description | Result on Violation |
| :--- | :--- | :--- | :--- |
| **Column Count** | Raw records | Must contain exactly 26 white-space separated numeric tokens per line. | Ingestion Abortion (ValidationError) |
| **Numeric Types** | All fields | Operational settings and sensor readings must parse as standard IEEE 754 floats. | Ingestion Abortion (ValidationError) |
| **Null/NaN Prevention** | Telemetry values | No raw token may be empty, NaN, or non-numeric string representation. | Ingestion Abortion (ValidationError) |
| **Entity Cycle Monotonicity** | Per machine | Ingested `source_cycle` must increment monotonically by +1 starting from cycle 1. | Ingestion Abortion (ValidationError) |
| **Cycle Gap Detection** | Per machine | Checks for missing intermediate cycles within an engine's operating life. | Ingestion Abortion (ValidationError) |
| **Duplicate Cycle Check** | Machine + Cycle | No engine may have duplicate telemetry rows for the same cycle. | Ingestion Abortion (ValidationError) |
| **Ground Truth Alignment** | `RUL_FD001.txt` | Ground-truth RUL vector must have exactly 100 non-negative integer values. | Ingestion Abortion (ValidationError) |
| **Channel Variance Analysis** | All 24 channels | Channels exhibiting $\sigma^2 = 0$ are cataloged for ML feature selection. | Quality Audit Record Persisted |

---

## 3. Invariant Channel Profile for FD001

The NASA C-MAPSS FD001 dataset operates under a single nominal operating condition (Sea Level). As documented in Phase 0 and verified mathematically on the ingested dataset during Phase 2, exactly **7 channels exhibit zero variance**:

### Invariant Channels ($\sigma = 0.0$):
1. **`op_setting_3`**: Trajectory operating parameter (Constant: 100.0)
2. **`sensor_1`**: Fan inlet temperature ($T2$) (Constant: 518.67 °R)
3. **`sensor_5`**: LPC inlet temperature ($T24$) (Constant: 14.62 °R)
4. **`sensor_10`**: Fan bypass static pressure ($P15$) (Constant: 1.30 psia)
5. **`sensor_16`**: Bypass fuel-air ratio ($damb$) (Constant: 0.03)
6. **`sensor_18`**: Demanded fan speed ($Nf_{dmd}$) (Constant: 2388.0 rpm)
7. **`sensor_19`**: Demanded corrected fan speed ($PCNfR_{dmd}$) (Constant: 100.0 rpm)

### Architectural Policy:
- **No Blind Row/Column Dropping:** Raw sensor columns are fully preserved in PostgreSQL `telemetry_records`.
- **Quality Audit Trail:** Invariant channels are flagged as formal records in `data_quality_issues`.
- **Preprocessing Catalog:** Active sensor channels (14 degradation sensors + 2 dynamic op settings = 16 dynamic features) are cataloged in `dataset_metadata.active_sensors` for downstream Phase 3 ML feature scalers.

---

## 4. Ground-Truth Data Quality Audit Results (FD001)

```
[Quality Gate Audit Summary]
Dataset: NASA C-MAPSS FD001
Total Engines Checked: 200 (100 Train, 100 Test)
Total Cycles Checked: 33,727
Missing Cycles: 0
Non-monotonic Cycle Ordering: 0
Null or NaN Values: 0
Duplicate Cycle Entries: 0
Corrupted File Lines: 0
Ground Truth RUL Entries: 100 (Range: [7, 145] cycles)
Invariant Channels Flagged: 7
Active Informative Channels: 15
Overall Quality Status: PASSED (100% Structural & Relational Integrity)
```
