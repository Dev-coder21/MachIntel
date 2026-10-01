# Recommended Platform Demonstration Script

This script outlines a structured, 10-minute end-to-end demonstration of the MachIntel platform. It operates strictly on authentic, persisted NASA C-MAPSS and MVTec AD records without fabricated data.

---

## Demo Script Walkthrough (10 Minutes)

### Phase 1: Authentication & Command Center (2 Minutes)
1. **Login**: Navigate to [http://localhost:3000/login](http://localhost:3000/login).
   - Sign in using an `ADMIN` or `OPERATOR` account (e.g. `admin` / configured password).
2. **Command Center Overview (`/`)**:
   - Point out the **Fleet Operational Status Ribbon**: 200 total turbofans (100 run-to-failure engines, 100 test engines).
   - Point out the **Operational Freshness Bar** (M12): Shows real persisted timestamps of the last background worker cycles for Evidence Materialization, Risk Engine, and Maintenance.
   - Point out the **Worker Cluster Health**: Confirms worker daemon is `HEALTHY` and actively heartbeating.

### Phase 2: Telemetry & Machine Health Diagnostics (2 Minutes)
3. **Machine Registry (`/machines`)**:
   - Filter by status (`CRITICAL` or `ELEVATED`).
   - Select asset **`TURBOFAN-ENG-001`**.
4. **Machine Detail View (`/machines/TURBOFAN-ENG-001`)**:
   - Show sensor telemetry trends: 21 explicit sensor channels across 192 operational cycles.
   - Highlight the rolling causal analytics window ($W=20$): mean, standard deviation, and degradation trajectory.
   - Switch to the **Prognostics Tab**: View the piecewise-linear target curve and model inference showing predicted Remaining Useful Life (RUL) and normalized Health Index ($HI$).

### Phase 3: Risk Evaluation & Alert Console (1.5 Minutes)
5. **Alert Triage Console (`/alerts`)**:
   - Review active alerts derived from `risk-policy-v1.0.0`.
   - Explain how alerts are deduplicated: no repetitive spam is generated if an alert is already open for the same machine and trigger condition.
   - Acknowledge or review an active alert with audit logging.

### Phase 4: Optical Visual Inspection Station (1.5 Minutes)
6. **Visual Inspection Station (`/inspections`)**:
   - Switch from machine telemetry to optical visual inspection (MVTec AD `metal_nut`).
   - Open inspection results: highlight the frozen WideResNet-50-2 PatchCore anomaly detector.
   - Show the pixel-level anomaly heatmap overlay identifying defect regions (bent, color, flip, scratch) compared against calibrated threshold ($\tau = 2.8155$).
7. **Inspection Analytics (`/analytics`)**:
   - Review the 15-bin anomaly score distribution histogram and confusion matrix grid.

### Phase 5: Evidence Intelligence & Maintenance Workflow (1.5 Minutes)
8. **Evidence Intelligence (`/evidence`)**:
   - Demonstrate the Evidence Layer: structured `EvidenceRecord` items categorized by domain (`MACHINE_HEALTH` vs `VISUAL_INSPECTION`).
   - Highlight strict domain separation: MachIntel never fabricates causal relationships between unrelated datasets.
9. **Maintenance Command Center (`/maintenance`)**:
   - Review draft work orders generated under `maintenance-policy-v1.0.0`.
   - Walk through the finite-state machine lifecycle (`OPEN` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `COMPLETED`).

### Phase 6: AI Inspector & Background Job Observability (1.5 Minutes)
10. **Controlled AI Inspector (`/ai-inspector`)**:
    - Click a suggested query: *"What is the current health state and evidence for TURBOFAN-ENG-001?"*
    - Observe the execution trace: read-only tool calls (`get_machine`, `get_machine_health_summary`, `get_machine_risk`).
    - Note the strict domain grounding, citation badges linking back to authoritative records, and limitations banner.
11. **Background Job Monitor (`/admin/jobs`)**:
    - View active worker heartbeat indicators and execution history.
    - Click **Trigger: Telemetry Completeness (`ANALYTICS_REFRESH`)** or **Evidence Materialization (`EVIDENCE_REFRESH`)**.
    - Watch the job transition from `QUEUED` $\rightarrow$ `RUNNING` $\rightarrow$ `SUCCEEDED` with real execution duration.
    - Open the inspect modal to verify the output summary JSON.
