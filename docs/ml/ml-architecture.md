# MachIntel Machine Learning Architecture — Milestone M4

## Executive Overview
Milestone M4 establishes the first genuine, end-to-end Machine Learning vertical slice for industrial turbofan Remaining Useful Life (RUL) regression and analytical health state tracking. The architecture transforms raw multivariate sensor cycles into causal rolling feature tensors, trains deterministic baseline regressors strictly on isolated training units, validates them on held-out units, evaluates them against official NASA competition ground truth, and serves real-time inferences with complete provenance tracking.

```mermaid
flowchart TD
    subgraph Data Layer [1. Telemetry Ingestion]
        CMAPSS[NASA C-MAPSS FD001<br/>33,727 Telemetry Cycles]
        SPLIT[Entity Isolation Split<br/>Train: Units 1–80<br/>Val: Units 81–100<br/>Test: Units 1–100]
    end

    subgraph Feature Engineering [2. Causal Feature Extraction]
        CONTRACT[Feature Contract v1.0.0<br/>Window: 20 cycles<br/>16 Active Channels]
        TRANSFORMS[Causal Statistics<br/>raw, mean, std, min, max, slope<br/>Total: 102 Feature Columns]
    end

    subgraph Preprocessing [3. Training-Fitted Preprocessing]
        SCALER[Robust Scaler<br/>Fit ONLY on Units 1–80<br/>Transform Val & Test]
    end

    subgraph Modeling [4. Baseline Models & Selection]
        RIDGE[Ridge Regression<br/>alpha=100.0]
        RF[Random Forest Regressor<br/>n=100, max_depth=12]
        SELECTION{Predefined Rule:<br/>Min Val RMSE}
        ACTIVE[Selected Active Model:<br/>rul-randomforest-v1.0.0]
    end

    subgraph Serving [5. Real Inference & State Interpretation]
        API[FastAPI Prediction Endpoint<br/>POST /machines/:id/predictions]
        CLAMP[Physical Bounds Clamping<br/>RUL >= 0]
        HI[Health Index Derivation<br/>HI = clamp(RUL / 125, 0, 1)]
        STATE[Analytical State Mapping<br/>NORMAL, WATCH, ELEVATED, CRITICAL]
        DB[(PostgreSQL 16<br/>predictions & model_registry)]
    end

    CMAPSS --> SPLIT
    SPLIT --> CONTRACT
    CONTRACT --> TRANSFORMS
    TRANSFORMS --> SCALER
    SCALER --> RIDGE & RF
    RIDGE & RF --> SELECTION
    SELECTION --> ACTIVE
    ACTIVE --> API
    API --> CLAMP --> HI --> STATE --> DB
```

## Architectural Tenets
1. **Zero Data Leakage:** Preprocessing transformations (e.g. median scaling, interquartile scaling) are fit strictly on internal training engines (Units 1–80). Validation and official test sets are transformed using frozen parameters.
2. **Strict Temporal Causality:** Features generated at cycle $t$ use only cycles $\le t$. No forward windowing or lookahead interpolations are permitted.
3. **Reproducible Model Registry:** Model weights, scalers, hyperparameters, and feature metadata are serialized to disk (`storage/models/rul/<version>/`) and tracked in the relational `model_registry` table.
4. **Honest Prognostic Language:** Predictions represent statistical remaining life estimates. Health indices represent deterministic analytical risk scores, not guaranteed safety determinations.
