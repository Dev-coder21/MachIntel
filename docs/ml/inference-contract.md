# Inference Contract & Health Index Interpretation

## Prognostic Inference Contract

### Input Specification
```json
{
  "observation_cycle": 150,
  "model_version": "rul-randomforest-v1.0.0"
}
```
- `observation_cycle` *(Optional[int])*: Specific historical operating cycle to evaluate. Defaults to the latest available cycle for the engine.
- `model_version` *(Optional[str])*: Model identifier from registry. Defaults to the active serving model.

### Output Specification
```json
{
  "id": "e0a2e838-5c08-47ca-b546-78b4e0ca95d7",
  "machine_id": "82fa34d0-f2b4-4d19-bd2f-7adfb94b263c",
  "machine_name": "TURBOFAN-ENG-001",
  "model_version": "rul-randomforest-v1.0.0",
  "dataset_version": "NASA-C-MAPSS-FD001",
  "feature_version": "1.0.0",
  "observation_cycle": 150,
  "predicted_rul": 42.1,
  "health_index": 0.3368,
  "operational_state": "ELEVATED",
  "created_at": "2026-10-01T04:29:10.512Z",
  "metadata_json": {
    "algorithm": "RandomForestRegressor",
    "raw_predicted_rul": 42.103,
    "feature_count": 102,
    "disclaimer": "Analytical risk interpretation derived from baseline statistical regression; not a certified safety determination."
  }
}
```

## Health Index & Analytical State Derivation

### Normalized Health Index
$$\text{HI} = \text{clamp}\left(\frac{\hat{\text{RUL}}}{125.0}, 0.0, 1.0\right)$$

### Deterministic Risk Thresholds
| Health Index Range | Analytical Health State | Color / Severity | Interpretation |
| :--- | :--- | :--- | :--- |
| $\text{HI} \ge 0.70$ | `NORMAL` | Emerald (`#10B981`) | Operating within nominal parameter margins |
| $0.40 \le \text{HI} < 0.70$ | `WATCH` | Cyan (`#06B6D4`) | Incipient wear trajectory observed |
| $0.15 \le \text{HI} < 0.40$ | `ELEVATED` | Amber (`#F59E0B`) | Substantial high-pressure compressor degradation |
| $\text{HI} < 0.15$ | `CRITICAL` | Rose (`#EF4444`) | Approaching end of operational cycle life |

## Non-Fabrication Policy
- **No Fabricated Confidence Intervals:** Standard Random Forest regression does not output calibrated epistemic uncertainty. Confidence intervals are strictly omitted rather than synthesized.
- **No Fabricated Probability-of-Failure:** Probabilities are not generated from regression models without survival analysis or calibrated failure density estimation.
- **Language Boundaries:** UI and API copy exclusively employ "Estimated Remaining Useful Life" and "Analytical Health State" rather than claims of guaranteed failure timing.
