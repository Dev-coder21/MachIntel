# Data & Temporal Leakage Prevention

## Principles of Zero Leakage
In machine-health predictive maintenance, subtle temporal and entity leakages represent the primary cause of artificially inflated performance metrics that fail in real-world deployment. MachIntel enforces strict architectural safeguards against all four standard failure modes.

## Safeguard 1: Entity-Level Split Isolation
- **Rule:** Telemetry cycles from a given engine must belong exclusively to a single split partition.
- **Implementation:** Units 1–80 are assigned to `INTERNAL_TRAIN`, Units 81–100 to `INTERNAL_VAL`, and official test engines to `EVAL_TEST`.
- **Validation:** Automated test `test_train_validation_entity_isolation` checks pairwise set disjointness:
  $$\text{Train} \cap \text{Val} = \emptyset, \quad \text{Train} \cap \text{Test} = \emptyset, \quad \text{Val} \cap \text{Test} = \emptyset$$

## Safeguard 2: Training-Fitted Preprocessing
- **Rule:** Normalization statistics (medians, quantiles, means) must be computed exclusively from the training split.
- **Implementation:** `RobustScaler` is fitted strictly on `INTERNAL_TRAIN` (Units 1–80). The fitted object is serialized to `scaler.joblib`. The validation and test splits are strictly passed to `.transform()`, never `.fit()` or `.fit_transform()`.

## Safeguard 3: Causal Rolling Windows (No Future Lookahead)
- **Rule:** Feature extraction at cycle $t$ must only process data from cycles $\tau \le t$.
- **Implementation:** In `FeatureExtractionService`, rolling statistics (mean, std, min, max, slope) over window $W=20$ are calculated using historical index slices $[t-W+1, t]$.
- **Validation:** Automated test `test_temporal_leakage_safeguard` verifies that feature vectors extracted with `end_cycle = 50` are bit-for-bit identical to the cycle 50 row extracted when querying the engine's entire trajectory.

## Safeguard 4: Official Test Set Ground Truth Protection
- **Rule:** Official test ground truth (`RUL_FD001.txt`) must never be used for training, feature transformation, hyperparameter selection, or model selection.
- **Implementation:** `RUL_FD001.txt` is loaded into the test engine records for final benchmark comparison only. The model selection rule evaluates solely on `INTERNAL_VAL`.
