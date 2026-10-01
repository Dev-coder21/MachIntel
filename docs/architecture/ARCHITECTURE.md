# MachIntel Technical Architecture Specification

## 1. System Overview & Monorepo Topology

MachIntel is an enterprise-grade industrial machine-health intelligence and optical inspection platform. Engineered exclusively for **local on-premises and containerized execution**, it eliminates external cloud platforms, cloud ML services, and unvetted shadow pipelines.

```mermaid
graph TB
    subgraph ClientLayer ["Client Layer (Next.js 15 / React 19 / TypeScript)"]
        UI_Dash["Command Center (/)"]
        UI_Machines["Machine Fleet (/machines)"]
        UI_Alerts["Alert Console (/alerts)"]
        UI_Maint["Maintenance Orders (/maintenance)"]
        UI_Prog["Prognostics & RUL (/predictions)"]
        UI_Insp["Visual Inspection (/inspections)"]
        UI_Analytics["Inspection Analytics (/analytics)"]
        UI_Evidence["Evidence Intelligence (/evidence)"]
        UI_AI["AI Inspector (/ai-inspector)"]
        UI_Models["Model Lifecycle (/admin/models)"]
        UI_Jobs["Worker Jobs (/admin/jobs)"]
    end

    subgraph APILayer ["Application & API Layer (FastAPI / Python 3.13)"]
        Router["FastAPI Router (/api/v1)"]
        AuthMiddleware["JWT Auth & RBAC Middleware"]
        CorrMiddleware["X-Request-ID & Security Headers"]
    end

    subgraph ServiceLayer ["Core Engines & Domain Services"]
        PredService["Prediction Service (RUL W=20)"]
        RiskEngine["Deterministic Risk Engine (HI -> State)"]
        AlertService["Deduplicated Alert Dispatcher"]
        InspService["PatchCore Optical Inspector"]
        EvidenceService["Evidence Materializer & Graph"]
        MaintService["Maintenance Workflow Engine"]
        AIService["Guarded AI Inspector (15 Tools)"]
        ModelService["Model Lifecycle & 8-Gate Registry"]
        JobService["ACID Job Queue Manager"]
    end

    subgraph WorkerLayer ["Background Workers Daemon"]
        WorkerDaemon["Worker Process (SELECT FOR UPDATE SKIP LOCKED)"]
        Heartbeat["Heartbeat & Lease Reaper"]
        JobHandlers["Idempotent Handlers (Refresh, Integrity)"]
    end

    subgraph PersistenceLayer ["Persistence & Storage Layer"]
        Postgres["PostgreSQL 16 (Authoritative Metadata Store)"]
        LocalFS["Local Filesystem (storage/models/ & storage/inspections/)"]
    end

    ClientLayer -->|REST / HTTPS / SSE| APILayer
    APILayer --> AuthMiddleware --> CorrMiddleware --> Router
    Router --> ServiceLayer
    ServiceLayer --> Postgres
    ServiceLayer --> LocalFS
    WorkerDaemon --> Postgres
    WorkerDaemon --> ServiceLayer
```

---

## 2. Machine Health Prognostic Pipeline (NASA C-MAPSS FD001)

The Machine Health vertical models progressive high-pressure compressor degradation across turbofan engines.

```mermaid
flowchart TD
    Raw["Raw Run-to-Failure Telemetry (21 Sensors / Cycles)"] --> InvarianceFilter["Channel Invariance Filter (7 Invariants Dropped)"]
    InvarianceFilter --> ActiveChannels["17 Active Channels (14 Sensors + 3 Op Settings)"]
    ActiveChannels --> CausalWindow["Causal Rolling Statistics Window (W=20)"]
    CausalWindow --> FeatVec["102 Engineered Features (Mean, Std, Min, Max, Slope)"]
    FeatVec --> Scaler["RobustScaler (Fitted on INTERNAL_TRAIN Units 1-80)"]
    Scaler --> Model["rul-randomforest-v1.0.0 (Scikit-Learn)"]
    Model --> RawRUL["Estimated RUL Output"]
    RawRUL --> TargetClamp["Piecewise Clamping: RUL* = min(125, max(0, RUL))"]
    TargetClamp --> HI["Health Index: HI = RUL* / 125 in [0.0, 1.0]"]
    HI --> RiskRules{"Risk Threshold Mapping"}
    RiskRules -->|HI >= 0.70| StateNorm["NORMAL (Nominal)"]
    RiskRules -->|0.40 <= HI < 0.70| StateWatch["WATCH (Minor Anomaly)"]
    RiskRules -->|0.15 <= HI < 0.40| StateElev["ELEVATED (Imminent Action)"]
    RiskRules -->|HI < 0.15| StateCrit["CRITICAL (Severe Degradation)"]
    StateCrit --> DedupeCheck{"Alert Deduplication Key"}
    DedupeCheck -->|Active Alert Exists| Suppress["Suppress Redundant Alert"]
    DedupeCheck -->|No Active Alert| DispatchAlert["Dispatch Alert & Trigger Maintenance"]
```

---

## 3. Optical Visual Inspection Pipeline (MVTec AD metal_nut)

The Visual Inspection vertical performs unsupervised optical surface defect detection and pixel-level localization.

```mermaid
flowchart TD
    LosslessImg["High-Resolution Optical Capture (700x700 Lossless PNG)"] --> Preproc["Standard Normalization (ImageNet Mean/Std)"]
    Preproc --> Backbone["Frozen Wide_ResNet50_2 Feature Extractor"]
    Backbone --> L2["Layer 2 Features (512d, 28x28 patch grid)"]
    Backbone --> L3["Layer 3 Features (1024d, 28x28 patch grid)"]
    L2 & L3 --> LocalAgg["3x3 Local Neighborhood Aggregation"]
    LocalAgg --> PatchSpace["1536-Dimensional Patch Embeddings (784 patches)"]
    PatchSpace --> NN["Nearest-Neighbor Distance vs 5% Coreset Memory Bank"]
    NN --> ScoreMap["28x28 Anomaly Distance Heatmap"]
    ScoreMap --> Bilinear["Bilinear Interpolation & Gaussian Smoothing (sigma=4)"]
    Bilinear --> AnomalyScore["Image Anomaly Score: s = max(Heatmap)"]
    AnomalyScore --> DecisionRule{"Decision Rule vs tau = 2.8155"}
    DecisionRule -->|s <= 2.8155| Pass["PASS (Within Normal Envelope)"]
    DecisionRule -->|s > 2.8155| Defect["DEFECT (Surface Anomaly Detected)"]
    Defect --> JetOverlay["Jet Heatmap & Localization Overlay Generation"]
    JetOverlay --> FSStorage["Persist to Local storage/inspections/"]
```

---

## 4. Evidence Lineage & Strict Domain Isolation

MachIntel categorically prohibits unvetted multimodal coupling.

```mermaid
graph TD
    subgraph MachineHealthDomain ["Domain 1: MACHINE_HEALTH (NASA C-MAPSS)"]
        E_Tele["Evidence: TELEMETRY (Sensor Cycles)"]
        E_Pred["Evidence: RUL_PREDICTION (Estimated RUL)"]
        E_HI["Evidence: HEALTH_INDEX (Normalized Score)"]
        E_Risk["Evidence: RISK_ASSESSMENT (State Evaluation)"]
        E_Alert["Evidence: ALERT (Deduplicated Incident)"]
        E_MaintMH["Evidence: MAINTENANCE_RECOMMENDATION (Engine Work Order)"]

        E_Tele -->|DERIVED_FROM| E_Pred
        E_Pred -->|EVALUATED_BY| E_HI
        E_HI -->|TRIGGERS| E_Risk
        E_Risk -->|EMITS| E_Alert
        E_Risk -->|RECOMMENDS| E_MaintMH
    end

    subgraph VisualInspectionDomain ["Domain 2: VISUAL_INSPECTION (MVTec AD)"]
        E_Img["Evidence: IMAGE (Optical Capture)"]
        E_Score["Evidence: ANOMALY_SCORE (Distance Metric)"]
        E_Heat["Evidence: LOCALIZATION (Pixel Anomaly Map)"]
        E_Dec["Evidence: INSPECTION_DECISION (PASS / DEFECT)"]
        E_MaintCV["Evidence: MAINTENANCE_RECOMMENDATION (Nut Work Order)"]

        E_Img -->|DERIVED_FROM| E_Score
        E_Score -->|LOCALIZED_BY| E_Heat
        E_Score -->|EVALUATED_BY| E_Dec
        E_Dec -->|RECOMMENDS| E_MaintCV
    end

    MachineHealthDomain -.->|REJECTED: CrossDomainEvidenceException (HTTP 422)| VisualInspectionDomain
```

---

## 5. Controlled AI Inspector Investigation Flow

The AI Inspector is an evidence-grounded decision-support forensic assistant.

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Plant Operator
    participant UI as AI Inspector UI (/ai-inspector)
    participant Engine as AI Inspector Orchestrator
    participant Sanitizer as Input / SQL Injection Defense
    participant Tools as 15 Read-Only Application Tools
    participant Grounding as Grounding & Citation Validator
    participant DB as PostgreSQL Audit Log

    Operator->>UI: Submit inquiry: "Why is machine 1 in CRITICAL state?"
    UI->>Engine: POST /api/v1/ai-inspector/investigate
    Engine->>Sanitizer: Sanitize input (check for SQL/Path Traversal/actuators)
    Sanitizer-->>Engine: Clean parameterized prompt
    Engine->>Tools: Execute read-only tool: get_machine(machine_id="TURBOFAN-ENG-001")
    Tools-->>Engine: Machine metadata + evidence_id
    Engine->>Tools: Execute read-only tool: get_machine_risk(machine_id="TURBOFAN-ENG-001")
    Tools-->>Engine: Risk state CRITICAL + reason codes + evidence_id
    Engine->>Grounding: Validate that all statements cite verified evidence_id
    Grounding-->>Engine: Verified grounded response + verified citations
    Engine->>DB: Persist trace in ai_investigations (Audit Trail)
    Engine-->>UI: Return formatted markdown findings + interactive citation badges
    UI-->>Operator: Display structured report + evidence links
```

---

## 6. Model Lifecycle & Deterministic Promotion Gates

Models progress through an explicit state machine with cryptographic integrity gates.

```mermaid
stateDiagram-v2
    [*] --> REGISTERED: Model Ingested & SHA-256 Calculated
    REGISTERED --> EVALUATED: Evaluated on Official Test Split
    REGISTERED --> REJECTED: Gate Failure / Bad Metadata
    EVALUATED --> CANDIDATE: Tagged for Serving Review
    EVALUATED --> REJECTED: Performance Below Threshold
    CANDIDATE --> PROMOTED: Passes All 8 Deterministic Gates
    CANDIDATE --> REJECTED: Failed Gate / Corrupted Binary
    PROMOTED --> RETIRED: Superseded by New Promoted Model
    RETIRED --> CANDIDATE: Re-activated via 8 Gates

    note right of PROMOTED
        Exactly 1 Active Model per Domain
        Gate 1: Artifact Exists
        Gate 2: SHA-256 Valid
        Gate 3: Dataset Valid
        Gate 4: Feature Config Valid
        Gate 5: Manifest Exists
        Gate 6: Required Metrics
        Gate 7: Evaluation Passed
        Gate 8: Domain Consistent
    end note
```

---

## 7. Background Worker & ACID Job Architecture

Background jobs execute deterministically via PostgreSQL transactional queues without Redis or Celery.

```mermaid
flowchart LR
    subgraph Trigger ["Job Producers"]
        Cron["Periodic Timer (Heartbeat)"]
        API["REST Trigger (POST /jobs/trigger)"]
        Service["Lifecycle Transition Trigger"]
    end

    subgraph Queue ["PostgreSQL background_jobs Table"]
        RowLock["Row-Level Lock: SELECT ... FOR UPDATE SKIP LOCKED"]
        IdempKey["Idempotency Key: {JOB_TYPE}:{TARGET_ID}"]
    end

    subgraph Workers ["Worker Daemon Process"]
        Daemon["Worker Loop (Async Signal Handlers)"]
        Exec["Job Handler Execution"]
        HeartbeatWorker["Heartbeat Updater (Every 10s)"]
    end

    subgraph Realtime ["Client Notification"]
        SSEStream["Server-Sent Events (/api/v1/jobs/events)"]
        JobUI["Job Monitor (/admin/jobs)"]
    end

    Trigger -->|INSERT background_jobs| Queue
    Queue --> RowLock --> Daemon
    Daemon --> Exec
    Daemon --> HeartbeatWorker
    Exec -->|UPDATE status=SUCCEEDED / FAILED| Queue
    Exec -->|Emit Event| SSEStream --> JobUI
```
