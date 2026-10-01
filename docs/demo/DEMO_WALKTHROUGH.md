# MachIntel Scripted Operational Demonstration Walkthrough (10 Minutes)

This script provides an authoritative, step-by-step, 10-minute reviewer walkthrough of MachIntel.
Every metric, chart, and alert in this demonstration operates on **authentic, persisted NASA C-MAPSS FD001 and MVTec AD `metal_nut` data** stored locally in PostgreSQL and the filesystem.

---

## Complete 15-Step Reviewer Journey

```
[1. Login] ─────────> [2. Dashboard] ────────> [3. Machines List] ─────> [4. Telemetry Stream]
                                                                                │
[8. Maintenance] <─── [7. Evidence Lineage] <─ [6. Risk & Alerts] <───── [5. RUL Prognostics]
       │
       ▼
[9. Visual Inspections] ──> [10. Anomaly Heatmaps] ──> [11. Domain Separation]
                                                                 │
[15. Worker Jobs] <─── [14. Model Lifecycle] <─ [13. Tool Trace] <─── [12. AI Inspector]
```

---

### Step 1: Secure Operator Login
- **URL**: [http://localhost:3000/login](http://localhost:3000/login)
- **Action**: Enter credentials for Administrator (`admin` / `AdminPassword2026!`) or Operator (`operator` / `OperatorPassword2026!`).
- **Narrative**:
  > *"MachIntel enforces role-based access control (RBAC). Roles include VIEWER (read-only audit), OPERATOR (triage alerts, manage work orders), and ADMIN (model lifecycle governance, system configuration). JWT tokens are issued with bounded lifetimes and cryptographic signing."*

---

### Step 2: Fleet Intelligence Command Center
- **URL**: [http://localhost:3000/](http://localhost:3000/)
- **Observation**:
  - **Fleet Status Ribbon**: 200 ingested turbofans (100 run-to-failure engines, 100 test engines) with 33,727 verified cycle records.
  - **Operational Freshness Bar**: Real timestamps of the last background worker cycles (`ANALYTICS_REFRESH`, `RISK_REFRESH`, `EVIDENCE_REFRESH`).
  - **Worker Daemon Health**: Verifies that the local worker daemon is actively heartbeating.
  - **Active Fleet Health State Breakdown**: Real distributions (`NORMAL`, `WATCH`, `ELEVATED`, `CRITICAL`).
- **Narrative**:
  > *"The Command Center answers 'What is happening across the industrial fleet right now?' without fabricating data. Every KPI reflects actual database rows and live inference models."*

---

### Step 3: Machine Fleet Navigation
- **URL**: [http://localhost:3000/machines](http://localhost:3000/machines)
- **Action**: Use the operational state filter pills to filter for `CRITICAL` or `ELEVATED` engines.
- **Select**: Asset **`TURBOFAN-ENG-001`**.
- **Narrative**:
  > *"We observe 200 distinct turbofan assets strictly partitioned into train (Units 1–80), internal validation (Units 81–100), and test (Units 1–100). Asset 001 is a run-to-failure engine exhibiting progressive high-pressure compressor degradation."*

---

### Step 4: Asset Story — Sensor Telemetry Stream
- **URL**: [http://localhost:3000/machines/TURBOFAN-ENG-001](http://localhost:3000/machines/TURBOFAN-ENG-001)
- **Observation**:
  - The **Asset Story Pipeline** at the top displays the causal progression: `TELEMETRY → HEALTH INDEX → ESTIMATED RUL → RISK STATE → EVIDENCE LINEAGE → ACTIVE ALERTS → MAINTENANCE ORDER`.
  - In the **Telemetry & Rolling Trends** tab, inspect Sensor 2 (T24 LPC Outlet Temp) and Sensor 3 (T30 HPC Outlet Temp) over 192 operational cycles.
  - Toggle between raw values, rolling statistics ($W=20$), and sensor drift percentage.
- **Narrative**:
  > *"Our feature pipeline uses causal rolling windows. It never incorporates future cycle readings, guaranteeing zero temporal leakage in operational inference."*

---

### Step 5: Asset Story — Prognostics & Estimated RUL
- **Action**: Click the **PROGNOSTICS & RUL** tab.
- **Observation**:
  - Model: `rul-randomforest-v1.0.0` (Active Production Model).
  - Estimated RUL: $\approx 1.31$ cycles.
  - Normalized Health Index: $HI \approx 0.0105$ (clamped: $HI = RUL / 125$).
  - Current Health State: `CRITICAL`.
- **Narrative**:
  > *"MachIntel models degradation using a piecewise-linear target $RUL^* = \min(125, T_{fail} - t)$. The model outputs an estimated RUL and Health Index; it does not claim to know the exact failure second, maintaining honest decision-support boundaries."*

---

### Step 6: Asset Story — Risk Evaluation & Alert Triage
- **URL**: [http://localhost:3000/alerts](http://localhost:3000/alerts)
- **Observation**:
  - `TURBOFAN-ENG-001` has generated a `CRITICAL` alert under `risk-policy-v1.0.0`.
  - Reason codes: `HEALTH_INDEX_CRITICAL`, `RUL_BELOW_CRITICAL_THRESHOLD`.
  - Scoped Deduplication Key: `TURBOFAN-ENG-001:CRITICAL:risk-policy-v1.0.0` ensures no redundant alert spam is created while the issue remains open.
- **Action**: Open the Triage modal and review the alert event lifecycle.

---

### Step 7: Asset Story — Evidence Lineage
- **URL**: [http://localhost:3000/evidence](http://localhost:3000/evidence)
- **Observation**:
  - Select domain `MACHINE_HEALTH`.
  - Filter for `TURBOFAN-ENG-001`.
  - Inspect the structured `EvidenceRecord` items connecting raw telemetry $\rightarrow$ feature extraction $\rightarrow$ RUL prediction $\rightarrow$ risk assessment $\rightarrow$ alert trigger.
- **Narrative**:
  > *"The Evidence Layer provides complete auditable provenance. When an auditor asks 'Why was this machine flagged?', we can trace the exact model version, feature vector, and telemetry window."*

---

### Step 8: Asset Story — Maintenance Work Orders
- **URL**: [http://localhost:3000/maintenance](http://localhost:3000/maintenance)
- **Observation**:
  - Notice the deterministic recommendation for `TURBOFAN-ENG-001`: `CRITICAL` priority work order generated under `maintenance-policy-v1.0.0`.
  - Review finite-state lifecycle: `OPEN` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `COMPLETED`.
- **Narrative**:
  > *"MachIntel provides human-in-the-loop decision support. It does NOT automatically issue SCADA/PLC commands or trigger equipment shutdowns without mandatory human review."*

---

### Step 9: Optical Visual Inspection Station
- **URL**: [http://localhost:3000/inspections](http://localhost:3000/inspections)
- **Observation**:
  - Switch to the second evidence vertical: **MVTec AD (`metal_nut`)**.
  - Review the run summary: 115 test images (22 `PASS`, 93 `DEFECT`).
  - Active Model: `mvtec-patchcore-metalnut-v1.0.0` (frozen WideResNet-50-2 backbone).

---

### Step 10: Defect Localization & Anomaly Heatmaps
- **Action**: Select a defective sample (e.g. `scratch_001` or `bent_001`).
- **Observation**:
  - Anomaly Score: e.g. $4.82$ vs calibrated threshold $\tau = 2.8155$.
  - View toggle: **Overlay**, **Heatmap**, **Original lossless capture**, and **Ground-truth mask**.
  - Point out pixel-level localization: the Jet heatmap pinpoints the exact scratch/crack geometry.

---

### Step 11: Domain Separation Principle
- **Explanation**:
  > *"A cornerstone of MachIntel is the refusal of fraudulent multimodal coupling. Turbofan telemetry from C-MAPSS and metal nut photos from MVTec AD are completely separate industrial domains. MachIntel segregates them into separate evidence streams and strictly rejects cross-domain causal links."*

---

### Step 12: Controlled AI Inspector
- **URL**: [http://localhost:3000/ai-inspector](http://localhost:3000/ai-inspector)
- **Action**: Click the suggested query:
  *"Why is machine 1 in CRITICAL risk state?"*
- **Click**: **INVESTIGATE**.

---

### Step 13: Tool Trace, Grounding & Citations
- **Observation**:
  - Observe the multi-step tool execution trace: `get_machine`, `get_machine_health_summary`, `get_machine_risk`.
  - Notice the read-only execution: zero actuator access, zero SQL generation.
  - Notice the grounded response citing specific `evidence_id` tokens.
  - Test cross-domain refusal: ask *"Did the surface scratch on the metal nut cause turbofan 1 to fail?"*
  - The AI Inspector explicitly refuses cross-domain coupling and cites domain isolation policy.

---

### Step 14: Model Lifecycle & Deterministic Promotion Gates
- **URL**: [http://localhost:3000/admin/models](http://localhost:3000/admin/models)
- **Observation**:
  - View active production models: `rul-randomforest-v1.0.0` and `mvtec-patchcore-metalnut-v1.0.0`.
  - Click **Inspect** on `rul-randomforest-v1.0.0`:
    - Review the **Reproducibility Manifest**: 17 channels, 102 rolling features, target capping at 125, hyperparameters.
    - Review the **Immutable Evaluations**: validation RMSE 19.5411, test RMSE 19.0187.
    - Click **Verify SHA-256**: Watch the system compute the local SHA-256 digest on demand and verify match with recorded registry hash `186cda72751d...`.
    - Review the **Deterministic 8-Gate Policy**: all eight gates evaluated and verified.
- **Narrative**:
  > *"MachIntel eliminates shadow models. Models cannot enter production without passing eight deterministic gates, and inference resolves exclusively through the registry with SHA-256 integrity verification."*

---

### Step 15: Background Worker Infrastructure & System Health
- **URL**: [http://localhost:3000/admin/jobs](http://localhost:3000/admin/jobs)
- **Observation**:
  - Inspect the worker daemon health: active heartbeats, zero stale leases.
  - As an Operator or Admin, click **Trigger Job**: `MODEL_INTEGRITY_CHECK` or `ANALYTICS_REFRESH`.
  - Observe the job lifecycle: `QUEUED` $\rightarrow$ `RUNNING` $\rightarrow$ `SUCCEEDED` with real execution durations.
  - Inspect the returned JSON payload confirming all artifacts were verified.

---

## Summary of Completed Walkthrough
The reviewer has inspected:
1. End-to-end telemetry prognosis on real run-to-failure engines.
2. Optical anomaly detection with deep patch embeddings and heatmaps.
3. Strict domain separation and auditability.
4. Human-in-the-loop maintenance workflow.
5. Evidence-grounded AI forensic investigation with zero hallucinations.
6. Local-first model registry with SHA-256 integrity and 8 deterministic promotion gates.
7. ACID background worker queues with real-time health monitoring.
