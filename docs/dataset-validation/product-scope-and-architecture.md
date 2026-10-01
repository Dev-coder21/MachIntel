# MachIntel Product Scope & Architecture Decision Record (ADR)

**Document Version:** 1.0 (Phase 0 Validation Sprint)  
**Maintained By:** MachIntel Engineering Core  
**Review Standard:** Section 1, Section 8, Section 12, & Section 15 of MachIntel Master Blueprint  

---

## 1. Product Scope Boundary Freeze

Based on the empirical findings of the Phase 0 Dataset & Product Validation Sprint, the product scope for MachIntel Version 1.0 is formally locked.

### 1.1 Real Supported Functionality (In-Scope for v1.0)
1. **User Authentication & Role-Based Access Control (RBAC):**
   - Secure login/logout with JWT session handling.
   - Roles: `Viewer` (read-only dashboards), `Engineer` (run inference, acknowledge alerts, log maintenance), and `Admin` (manage machines, datasets, model metadata).
2. **Machine Registry & Asset Topology:**
   - Multi-asset registry supporting distinct machine categories:
     - **Dynamic Machinery Assets** (e.g. C-MAPSS Turbofan Fleet `TURBOFAN-ENG-001` through `100`).
     - **Automated Optical Inspection Stations** (e.g. `AOI-STATION-01` inspecting `metal_nut` industrial fasteners).
   - CRUD operations, health state indicators, and complete operational metadata.
3. **Reproducible Telemetry Ingestion & Validation:**
   - Ingestion of NASA C-MAPSS FD001 cycle records via structured CSV/JSON API endpoints.
   - Schema validation, range verification, missingness detection, and immutable batch tracking.
4. **Machine Analytics & Time-Series Visualizations:**
   - Interactive sensor trends across 14 informative channels ($T_{24}, T_{30}, T_{50}, P_{30}, N_f, N_c$, etc.).
   - Downsampled / aggregated rendering preventing browser performance degradation.
5. **Machine Health ML Inference (Prognostics):**
   - Serving of trained, versioned prognostic models predicting Remaining Useful Life (RUL) and normalized Health Index ($HI \in [0.0, 1.0]$).
   - Traceable predictions persisted with feature window metadata and model version hash.
6. **Industrial Visual Inspection Station (CV):**
   - Drag-and-drop image upload supporting genuine high-resolution industrial fastener images.
   - Unsupervised defect detection returning anomaly score, PASS/DEFECT classification, and localized defect heatmap/overlay mask.
   - Inspection history preserving original image URI, processed overlay URI, and audit metadata.
7. **Unified Evidence Layer & Explainable Risk Engine:**
   - Decoupled `TelemetryEvidence` and `VisualEvidence` schema aggregated into deterministic asset risk states (`NORMAL`, `WATCH`, `ELEVATED`, `CRITICAL`).
   - Audit trail of triggering evidence with transparent reason codes.
8. **Alert Management & Maintenance Lifecycle:**
   - Configurable alert policies triggered by prognostic health index breaches or visual defects.
   - Full lifecycle management: `OPEN` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `RESOLVED`.
   - Maintenance work-order logging linked to specific alerts and machines.
9. **AI Inspector (Grounded Forensic Assistant):**
   - Tool-augmented LLM investigation interface restricted strictly to read-only API calls.
   - Guaranteed evidence grounding citing specific telemetry windows, inspection IDs, and reason codes without hallucinations or cross-modal fabrications.
10. **Local Docker Environment:**
    - Single-command orchestration via `docker compose` running frontend, backend, PostgreSQL database, and local artifact storage.

---

### 1.2 Functionality Requiring Future Datasets (Deferred to v2.0 Roadmap)
1. **Joint End-to-End Multimodal Model:**
   - Merging sensor time series and optical imagery into a single cross-modal neural network. Requires synchronized, co-located physical asset data (such as bearing testbenches with paired acoustic, thermal, and optical cameras).
2. **3D Point Cloud Inspection:**
   - Parsing point-cloud (.pcd) files from MVTec 3D-AD.
3. **Complex Structural/Logical Assembly Inspection:**
   - Evaluating multi-part kit configurations from MVTec LOCO AD / AD 2.
4. **Automated Online Continuous Retraining:**
   - Production self-updating models; deferred until continuous ground truth feedback loops are established.

---

### 1.3 Functionality Explicitly Out of Scope
1. **Cloud Deployment (AWS / GCP / Azure):**
   - Per explicit project mandate, MachIntel will NOT be deployed to remote cloud providers. It is engineered for self-contained, reproducible local development and on-premises Docker execution.
2. **Direct Industrial Machine Actuation:**
   - MachIntel does NOT issue control commands, shut down physical machinery, or interface with industrial PLCs via SCADA/Modbus protocols.
3. **Certified Safety-Critical Decision Automation:**
   - MachIntel is a decision-support and intelligence platform, not a safety-certified emergency shutdown system.
4. **Synthetic Data Fabrication:**
   - No mock telemetry generators, fabricated defect masks, or synthetic cross-modal mappings will be presented as production data.

---

## 2. Target System Architecture

```
+-----------------------------------------------------------------------------------+
|                         CLIENT LAYER (Next.js / React)                            |
|                                                                                   |
|  - Industrial Dark Graphite / Deep Navy Command Center Interface                  |
|  - Fleet Dashboard & Real-Time Risk State Matrix                                  |
|  - Machine Detail View (Sensor Timelines, Degradation Trends, RUL Curves)         |
|  - Visual Inspection Station (Upload, Defect Localization Mask Overlay)           |
|  - AI Inspector Investigation Console (Evidence citations & tool inspection)      |
|  - Alert Queue & Closed-Loop Maintenance Logging                                  |
+-----------------------------------------------------------------------------------+
                                         |
                                         | REST / HTTPS (JSON)
                                         v
+-----------------------------------------------------------------------------------+
|                     APPLICATION & API LAYER (FastAPI)                             |
|                                                                                   |
|  Routers:                                                                         |
|  ├── /auth (JWT Authentication & RBAC Dependencies)                               |
|  ├── /machines (Asset Registry & Topology)                                        |
|  ├── /telemetry (Ingestion, Validation, Time-Series Queries)                      |
|  ├── /predictions (RUL & Health Index Inference Service)                          |
|  ├── /inspections (CV Image Upload & PatchCore Anomaly Service)                   |
|  ├── /evidence (Evidence Layer Aggregation & Unified Timelines)                   |
|  ├── /alerts (Alert Rule Evaluation & Lifecycle Management)                       |
|  ├── /maintenance (Work Order Records & Machine Links)                            |
|  ├── /analytics (Fleet-wide KPI Aggregations & Sensor Statistics)                 |
|  └── /ai-inspector (Tool Orchestrator with Read-Only Guards)                      |
+-----------------------------------------------------------------------------------+
        |                                                           |
        | Model Execution                                           | SQL / Object Storage
        v                                                           v
+------------------------------------+      +---------------------------------------+
|         ML / CV ENGINE             |      |           PERSISTENCE LAYER           |
|                                    |      |                                       |
|  - Prognostic RUL Pipeline:        |      |  PostgreSQL 16:                       |
|    - Sliding window (W=20)         |      |  - users & audit_logs                 |
|    - Scaler & rolling statistics   |      |  - machines & data_sources            |
|    - Random Forest / Ridge Model   |      |  - telemetry_records (indexed)        |
|  - Visual Inspection Pipeline:     |      |  - predictions & model_registry       |
|    - WideResNet-50-2 Backbone      |      |  - inspections & inspection_regions   |
|    - PatchCore Coreset Memory Bank |      |  - evidence_objects & alerts          |
|    - Anomaly Map & PRO Evaluator   |      |  - maintenance_records                |
|  - Model Registry & Checksums      |      |  Local Object Storage (Artifacts):    |
+------------------------------------+      |  - /inspections/raw/{id}.png          |
                                            |  - /inspections/overlays/{id}.png     |
                                            |  - /models/{model_name}/{v}/artifact  |
                                            +---------------------------------------+
```

---

## 3. Component Architecture Decisions

### 3.1 Telemetry Vertical
- **Ingestion:** Validates incoming C-MAPSS sensor payloads against 26-column schema. Rejects NaN, inf, or duplicate cycle entries.
- **Preprocessing:** Applies pre-fitted MinMaxScaler across 14 informative channels; drops invariant sensors ($1, 5, 10, 16, 18, 19$ and `op_setting_3`).
- **Inference:** Extracts 20-cycle rolling statistical summaries and queries the versioned RUL regression model artifact.
- **Output:** Writes prediction record containing cycle timestamp, predicted RUL, normalized Health Index, and model version.

### 3.2 Computer Vision Vertical
- **Ingestion:** Validates image file headers (PNG/JPEG), file size limit (10MB), and dimensions ($700 \times 700$).
- **Inference:** Runs the frozen WideResNet backbone patch extractor, compares patch vectors against the nominal memory bank, and generates a normalized anomaly heatmap.
- **Localization:** Computes binary defect contour mask based on the calibrated threshold $\tau$ ($\alpha = 0.01$).
- **Storage:** Stores raw uploaded image and rendered defect mask overlay into the local artifact repository; persists metadata, anomaly score, and bounding polygon in PostgreSQL.

### 3.3 Evidence & Risk Layer
- **Decoupling:** Decouples ingestion pipelines from downstream consumer interfaces.
- **Standardization:** All model outputs emit immutable `EvidenceObject` records with explicit timestamps and provenance.
- **State Machine:** Evaluates deterministic risk rules over the latest evidence objects to compute machine states: `NORMAL` $\rightarrow$ `WATCH` $\rightarrow$ `ELEVATED` $\rightarrow$ `CRITICAL`.
- **Reason Codes:** Every state change records explicit reason codes (e.g. `CODE_RUL_CRITICAL_BELOW_15_CYCLES`, `CODE_OPTICAL_DEFECT_DETECTED`).

### 3.4 AI Inspector Tool Suite
The AI Inspector is prohibited from executing unconstrained SQL or generating unfactual responses. It interacts strictly through typed read-only tool functions:
- `get_machine(machine_id)`
- `get_sensor_history(machine_id, start_cycle, end_cycle, sensors)`
- `get_latest_prediction(machine_id)`
- `get_recent_inspections(machine_id, limit)`
- `get_alerts(machine_id, status)`
- `get_maintenance_history(machine_id)`
- `get_evidence_timeline(machine_id)`
- `get_model_info(model_id)`

Each tool validates inputs, enforces row limits, and returns sanitized structured JSON context for grounded LLM synthesis.
