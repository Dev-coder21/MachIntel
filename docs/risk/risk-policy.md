# Risk Policy & Versioning Specification

## Policy Architecture

Operating thresholds and risk policies in MachIntel are maintained as versioned configuration structures rather than scattered magic numbers. Every persisted risk assessment and alert records the active policy version under which it was generated.

The current active policy version is:
```text
risk-policy-v1.0.0
```

---

## Configuration Specification

Defined in `backend/app/core/risk_policy.py`:

```python
RiskPolicyConfig(
    version="risk-policy-v1.0.0",
    description="Initial deterministic operational risk policy for NASA C-MAPSS FD001 prognostics",
    hi_normal_threshold=0.70,     # HI >= 0.70 -> NORMAL
    hi_watch_threshold=0.40,      # 0.40 <= HI < 0.70 -> WATCH
    hi_elevated_threshold=0.15,   # 0.15 <= HI < 0.40 -> ELEVATED
    # HI < 0.15 -> CRITICAL
    
    rul_max=125.0,                # Piecewise linear RUL clipping horizon
    rul_critical_threshold=18.75, # 0.15 * 125
    rul_elevated_threshold=50.0,  # 0.40 * 125
    rul_watch_threshold=87.5,     # 0.70 * 125
    
    rapid_decline_cycle_window=10,
    rapid_decline_rul_drop=25.0,
    
    alert_severity_map={
        "WATCH": "INFO",
        "ELEVATED": "WARNING",
        "CRITICAL": "CRITICAL"
    },
    deduplication_scope="machine_id:risk_state:policy_version",
    deduplicate_active_only=True
)
```

---

## Versioning & Evolution Principles

1. **Immutable Historical Records**:
   Modifying a policy configuration does not retroactively rewrite historical risk assessments. Assessments retain the `threshold_policy_version` active at evaluation time.
2. **Deterministic Regression Tests**:
   Changes to thresholds or severity mappings require a new version identifier (e.g. `risk-policy-v1.1.0` or `risk-policy-v2.0.0`) and accompanying unit tests verifying backward compatibility.
3. **Audit Trail**:
   All policy evaluations and threshold evaluations are logged to the audit log with the executing actor.
