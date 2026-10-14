# Temporal Leakage Safeguards & Causality Rules

## 1. The Core Threat in Industrial Prognostics
In remaining useful life (RUL) estimation and degradation forecasting, **temporal leakage** (data leakage across time or entities) artificially inflates model performance during validation while causing catastrophic failure in real-world deployment.

Common leakage vulnerabilities in naive predictive maintenance systems include:
1. **Future Lookahead:** Centered rolling windows (e.g. `rolling(window=20, center=True)`) that use future observations $t+1, \dots, t+10$ to evaluate degradation at cycle $t$.
2. **Global Normalization Leakage:** Fitting feature scalers (min/max/mean/std) on the entire dataset—including evaluation test engines and future operational cycles.
3. **Cross-Entity Bleed:** Computing rolling windows or differences across the boundary separating Engine #1 and Engine #2.
4. **Random Row Splitting:** Shuffling telemetry cycles into train/test sets, allowing identical engine states to appear simultaneously in training and test sets.

---

## 2. MachIntel Causality Safeguards

To prevent temporal and entity leakage, MachIntel enforces five hard architectural rules:

### Rule 1: Strictly Trailing Causal Windows
The window $\mathcal{W}_t$ at cycle $t$ is strictly trailing:
$$\mathcal{W}_t = [ \max(1, t - W + 1), t ]$$
- **Enforcement:** Verified in [test_rolling_feature_temporal_causality](../../backend/tests/test_analytics.py#L38-L76). Drastically altering all telemetry values from cycle 11 onwards produces exactly $0.0$ change in all rolling features at cycles $t \le 10$.

### Rule 2: Absolute Entity Isolation
Features are extracted strictly on a per-engine basis:
- **Enforcement:** Verified in [test_machine_boundary_isolation](../../backend/tests/test_analytics.py#L80-L101). Rolling windows reset cleanly to cycle 1 for every engine, with $\sigma_1 = 0.0$ and no cross-machine contamination.

### Rule 3: Entity-Preserving Data Split Allocation
Telemetry rows are partitioned by complete machine entity:
- **`INTERNAL_TRAIN` (Units 1–80):** 16,635 cycles.
- **`INTERNAL_VAL` (Units 81–100):** 3,996 cycles.
- **`EVAL_TEST` (Test Units 1–100):** 13,096 cycles.
- **Enforcement:** Hard database constraints and split badges. Random row splitting is prohibited.

### Rule 4: Causal Scaler Fitting Policy (M4 Contract)
Feature scalers must be fitted **only** on the training set:
$$\mu_{scaler}, \sigma_{scaler} \leftarrow \text{Fit}(\text{Units } 1 \dots 80)$$
$$\text{Transform}(\text{Units } 81 \dots 100), \quad \text{Transform}(\text{Test Units } 1 \dots 100)$$
- **Enforcement:** Codified in `FeatureEngineeringContract.scaling_policy = "FIT_ON_INTERNAL_TRAIN_ONLY"`.

### Rule 5: Discrete Operating Cycles as Authoritative Progression
No artificial wall-clock timestamps are fabricated. Flight cycles ($1, 2, \dots$) provide the authoritative ground-truth ordering for all rolling computations.
