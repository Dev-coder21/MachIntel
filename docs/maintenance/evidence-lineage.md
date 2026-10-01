# Maintenance Evidence Lineage & Integration

## 1. M8 Evidence Integration

The Maintenance Workflow layer extends the M8 Evidence Intelligence subsystem by treating maintenance items and verified outcomes as first-class evidence entities.

### Maintenance Evidence Types
1. `MAINTENANCE_RECOMMENDATION`: Created automatically when an OPEN work order is drafted from diagnostic or prognostic findings. Quality state is `DERIVED`.
2. `MAINTENANCE_OUTCOME`: Created only when an operator records an authentic completed resolution. Quality state is `VERIFIED`.

### Directed Relationships
- `MAINTENANCE_RECOMMENDATION` $\xrightarrow{\text{DERIVED\_FROM}}$ `RISK_ASSESSMENT` / `INSPECTION_RESULT`
- `MAINTENANCE_OUTCOME` $\xrightarrow{\text{DOCUMENTS}}$ `MAINTENANCE_RECOMMENDATION`

```
[ Domain: MACHINE_HEALTH ]
C-MAPSS FD001 Telemetry Record
        │
        ▼ (DERIVED_FROM)
Engineered Causal Features
        │
        ▼ (DERIVED_FROM)
RUL Regression Prediction
        │
        ▼ (DERIVED_FROM)
RiskAssessment (CRITICAL / ELEVATED)
        │
        ▼ (DERIVED_FROM)
Maintenance Recommendation Work Order
        │
        ▼ (DOCUMENTS)
Maintenance Outcome Record (Human Operator Verified)
```

```
[ Domain: VISUAL_INSPECTION ]
MVTec AD metal_nut Source Image
        │
        ▼ (PRODUCED_BY)
PatchCore Memory-Bank Anomaly Score & Heatmap
        │
        ▼ (DERIVED_FROM)
InspectionResult (DEFECT)
        │
        ▼ (DERIVED_FROM)
Maintenance Recommendation Work Order
        │
        ▼ (DOCUMENTS)
Maintenance Outcome Record (Human Operator Verified)
```

---

## 2. Prevention of Fabricated Outcomes

MachIntel strictly forbids simulating or generating automated maintenance completions:
- Completed outcomes are **never fabricated**.
- An `EvidenceRecord` of type `MAINTENANCE_OUTCOME` is only minted when a human operator with authenticated `OPERATOR` or `ADMIN` credentials invokes `/complete` with verified `resolution_notes`.
- Provenance captures the actor's ID, timestamp, and human-supplied resolution text.
