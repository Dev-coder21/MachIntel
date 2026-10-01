# Evidence Layer Specification & Data Contract

## Purpose & Scope

The MachIntel Evidence Layer provides an auditable, immutable, and verifiable trace from physical sensor observations to high-level risk assessments. Every claim made in the MachIntel user interface and API originates from a concrete, persisted Evidence Object.

MachIntel strictly adheres to the principle:
> **No fabricated confidence. No synthetic metrics. If confidence is uncalibrated or unavailable, it must be explicitly null/absent.**

---

## Standardized Evidence Object Schema

The `EvidenceObject` structure is defined in `backend/app/schemas/evidence.py`:

```python
class EvidenceObject(BaseModel):
    evidence_id: str                      # Unique UUID for the evidence record
    machine_id: str                       # Target machine identifier (e.g. TURBOFAN-ENG-001)
    evidence_type: str                    # Type: PREDICTED_RUL, HEALTH_INDEX, SENSOR_DRIFT, etc.
    source: str                           # Source engine: PROGNOSTIC_MODEL, TELEMETRY_STREAM, etc.
    source_reference: str                 # Pointer to authoritative record ID (e.g. prediction UUID)
    observation_cycle: int                # Physical operating cycle of observation
    observed_at: Optional[datetime]       # Wall-clock timestamp if available
    value: Any                            # Measured or inferred numeric value
    unit: Optional[str]                   # Physical unit (cycles, psia, deg R, etc.)
    confidence: Optional[float]           # Calibration score in [0.0, 1.0], or None if uncalibrated
    provenance: Dict[str, Any]            # Detailed lineage metadata dictionary
    model_version: Optional[str]          # Version identifier of ML artifact (e.g. rul-ridge-v1.0.0)
    feature_version: Optional[str]        # Version identifier of feature pipeline (e.g. 1.0.0)
    created_at: datetime                  # Record creation timestamp
```

---

## C-MAPSS Prediction Evidence Lineage

For prognostic regression evidence on NASA C-MAPSS FD001:

1. **Source Reference**:
   Points directly to the primary key (`id`) of the authoritative `Prediction` database record.
2. **Provenance Record**:
   Contains:
   - `dataset_identifier`: `"NASA-C-MAPSS-FD001"`
   - `model_id`: Active model identifier (e.g. `"rul-ridge-v1.0.0"`)
   - `algorithm`: Regression algorithm name (e.g. `"Ridge"`)
   - `window_size`: Causal rolling window horizon ($W=20$)
   - `scaler`: Normalization transformer (`"RobustScaler"`)
   - `features_used`: Number of features ($K=96$)
3. **Confidence Handling**:
   Standard deterministic regression models (Ridge, RandomForest) output point predictions without Bayesian or conformal prediction intervals. Therefore, `confidence` is stored strictly as `None` (`null`), avoiding deceptive pseudo-certainty.

---

## Presentation in UI

The evidence chain is presented in the frontend via `<EvidenceChain />`:
```text
C-MAPSS Telemetry (Cycle N)
        ↓
Ridge Regressor (rul-ridge-v1.0.0)
        ↓
Estimated RUL: X.X cycles
        ↓
Health Index: 0.XXX
        ↓
Deterministic Risk State (CRITICAL / ELEVATED / WATCH / NORMAL)
        ↓
Reason Codes & Audited Record References
```
