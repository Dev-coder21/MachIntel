# Risk Engine Specification & Architecture

## Overview

The MachIntel Risk Engine is a strictly deterministic operational intelligence layer positioned between raw ML prognostic inference (Remaining Useful Life regression) and operational dispatch (Alerts & Triage).

The core principle governing the Risk Engine is:
> **MachIntel must never say: "The machine will fail."**
> Instead, MachIntel states:
> - *"Analytical risk state: ELEVATED"*
> - *"Estimated Remaining Useful Life: X cycles"*
> - *"Risk state derived from model output and configured thresholds."*

These evaluations represent analytical operational risk states based on empirical data, never safety-critical or guaranteed failure predictions.

---

## Architectural Flow

```
+-----------------------------------------------------------+
|                  NASA C-MAPSS FD001 Telemetry             |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|          Causal Feature Pipeline (W=20, RobustScaler)     |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|          Authoritative Prognostic Model (rul-ridge-v1.0.0)|
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|               Persisted Prediction Record                 |
|  - predicted_rul (e.g. 18.4 cycles)                       |
|  - health_index (HI = clamp(RUL / 125, 0, 1) = 0.147)     |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|              Deterministic Risk Engine                    |
|  - Threshold Policy: risk-policy-v1.0.0                   |
|  - HI Mapping: HI < 0.15 -> CRITICAL                     |
|  - Rapid Decline Evaluation (historical delta)            |
|  - Reason Code Synthesis                                  |
|  - Human-Readable Explanation Generation                  |
|  - Evidence Object Compilation                            |
+-----------------------------------------------------------+
                             |
         +-------------------+-------------------+
         |                                       |
         v                                       v
+-------------------------------+ +-------------------------------+
|    RiskAssessment Record      | |      Alert Engine & Dispatch  |
| - Persisted in PostgreSQL     | | - Deterministic Deduplication |
| - State Transition Recorded   | | - Severity Mapping            |
| - Audit Log Entry             | | - Operator Triage Lifecycle   |
+-------------------------------+ +-------------------------------+
```

---

## Deterministic Risk State Mapping

The Risk Engine consumes the authoritative Health Index ($HI \in [0.0, 1.0]$) and maps it deterministically according to the configured threshold policy:

| Health Index Range | Risk State | Semantic Meaning | Alert Severity |
| :--- | :--- | :--- | :--- |
| $HI \ge 0.70$ | `NORMAL` | Nominal operational baseline; degradation within margins | None (no alert) |
| $0.40 \le HI < 0.70$ | `WATCH` | Incipient degradation drift; advisory monitoring recommended | `INFO` |
| $0.15 \le HI < 0.40$ | `ELEVATED` | Accelerated degradation; schedule inspection | `WARNING` |
| $HI < 0.15$ | `CRITICAL` | Severe degradation; imminent end-of-life threshold | `CRITICAL` |

---

## Reason Codes

Reason codes provide programmatic, machine-parseable explanations of every triggered factor:

1. **`HEALTH_INDEX_CRITICAL`**: Health Index dropped below 0.15.
2. **`RUL_BELOW_CRITICAL_THRESHOLD`**: Estimated RUL is $\le 18.75$ cycles.
3. **`HEALTH_INDEX_ELEVATED`**: Health Index is between 0.15 and 0.40.
4. **`RUL_BELOW_ELEVATED_THRESHOLD`**: Estimated RUL is $\le 50.0$ cycles.
5. **`HEALTH_INDEX_WATCH`**: Health Index is between 0.40 and 0.70.
6. **`RUL_BELOW_WATCH_THRESHOLD`**: Estimated RUL is $\le 87.5$ cycles.
7. **`RAPID_RUL_DECLINE`**: Historical RUL declined by $\ge 25.0$ cycles across $\le 10$ operational cycles.

---

## Determinism & Boundary Conditions

- Given identical inputs (prediction, machine history, policy version), the Risk Engine will always produce identical output (`risk_state`, `reason_codes`, and `explanation`).
- Boundary values:
  - Exactly $HI = 0.70 \rightarrow \text{NORMAL}$
  - Exactly $HI = 0.40 \rightarrow \text{WATCH}$
  - Exactly $HI = 0.15 \rightarrow \text{ELEVATED}$
  - Exactly $HI = 0.1499 \rightarrow \text{CRITICAL}$
