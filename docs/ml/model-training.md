# Model Training & Pipeline Implementation

## Split Isolation Strategy
The data foundation separates the 200 NASA C-MAPSS FD001 machines into three mutually exclusive entity partitions:

| Split Name | Entity Range | Machine Count | Cycles / Samples | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `INTERNAL_TRAIN` | Units 1–80 | 80 engines | 16,138 cycles | Fit scaler & optimize model weights |
| `INTERNAL_VAL` | Units 81–100 | 20 engines | 4,493 cycles | Model selection & hyperparameter evaluation |
| `EVAL_TEST` | Test Units 1–100 | 100 engines | 100 final vectors | Final frozen benchmark against `RUL_FD001.txt` |

Entity isolation guarantees zero leakage: no observation from an engine in validation or test appears in the training matrix.

## Feature Representation
- **Feature Contract Version:** `1.0.0`
- **Rolling Window Size ($W$):** 20 cycles
- **Active Channels (17):**
  - Operational Settings: `op_setting_1`, `op_setting_2`
  - Sensor Channels: `sensor_2`, `sensor_3`, `sensor_4`, `sensor_6`, `sensor_7`, `sensor_8`, `sensor_9`, `sensor_11`, `sensor_12`, `sensor_13`, `sensor_14`, `sensor_15`, `sensor_17`, `sensor_20`, `sensor_21`
- **Transformations per Channel (6):**
  - `raw`: Current instantaneous reading
  - `rolling_mean`: 20-cycle causal moving average
  - `rolling_std`: 20-cycle causal standard deviation
  - `rolling_min`: 20-cycle causal minimum
  - `rolling_max`: 20-cycle causal maximum
  - `rolling_slope`: 20-cycle causal linear trend rate
- **Total Input Dimensionality:** $17 \times 6 = 102$ features.

## Preprocessing Pipeline
- **Method:** `sklearn.preprocessing.RobustScaler`
- **Fit Domain:** Strictly on `INTERNAL_TRAIN` (Units 1–80).
- **Transform Domain:** Applied to `INTERNAL_VAL` and `EVAL_TEST` using frozen training quantiles.
- **Persistence:** Serialized as `scaler.joblib` alongside the model artifact.

## Baseline Algorithms
1. **Ridge Regression:**
   - Hyperparameters: $\alpha = 100.0$, `random_state = 42`
   - Purpose: Linear baseline with $L_2$ regularization to prevent collinear overfitting across correlated sensor channels.
2. **Random Forest Regressor:**
   - Hyperparameters: `n_estimators = 100`, `max_depth = 12`, `min_samples_split = 5`, `random_state = 42`, `n_jobs = -1`
   - Purpose: Non-linear ensemble model capturing non-linear degradation dynamics.

## Execution
Training is completely reproducible via the CLI:
```bash
backend/.venv/bin/python backend/scripts/train_models.py
```
