# Maintenance Workflow Architecture (Milestone M9)

## 1. Operational Overview & Boundaries

MachIntel Maintenance Workflow is a **human-in-the-loop operational decision support and auditability layer**. It bridges validated diagnostic/prognostic evidence with controlled human operational workflows.

### Strict Safety & Autonomous Action Boundaries
MachIntel is **NOT** an autonomous maintenance or industrial control system. MachIntel strictly adheres to the following non-negotiable operational principles:
- **No Direct Machine Control:** MachIntel never issues commands to physical actuators, servo drives, valves, or relays.
- **No SCADA / PLC Interfacing:** MachIntel does not communicate directly with industrial Programmable Logic Controllers or SCADA command loops.
- **No Automatic Shutdowns:** MachIntel never automatically trips or shuts down operating equipment.
- **No Guaranteed Failure Claims:** Models predict statistical Remaining Useful Life ($RUL$) and anomaly distances; they never claim infallible foresight.
- **Human Review Mandatory:** Every maintenance work order recommendation requires human review, assignment, execution, and outcome verification by certified engineering operators.

```
       AUTHENTIC EVIDENCE
               │
               ▼
┌───────────────────────────────┐
│     EVIDENCE INTELLIGENCE     │
│  (C-MAPSS Telemetry & MVTec)  │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│    RISK / VISION DEFECT       │
│  Deterministic Evaluation     │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│  MAINTENANCE RECOMMENDATION   │
│   Policy-Driven Draft Order   │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│     HUMAN WORKFLOW REVIEW     │
│   Acknowledge → Start → Res   │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│     VERIFIED AUDIT LOG        │
│   Immutable Events & Evidence │
└───────────────────────────────┘
```

---

## 2. Database Schema & Tables

The maintenance domain is persisted across two relational PostgreSQL tables created in migration `d1e2f3a4b5c6_create_maintenance_workflow_tables.py`:

### Table: `maintenance_work_orders`
Stores authoritative work order entities, evidence snapshots, lifecycle status, and attribution.

| Column | Type | Constraints / Description |
|---|---|---|
| `id` | `UUID` | Primary Key, default `uuid4` |
| `machine_id` | `VARCHAR(100)` | Indexed; populated for `MACHINE_HEALTH`, NULL for `VISUAL_INSPECTION` |
| `source_domain` | `VARCHAR(50)` | Indexed; strictly `MACHINE_HEALTH` or `VISUAL_INSPECTION` |
| `source_type` | `VARCHAR(50)` | Indexed; `RISK_ASSESSMENT`, `ALERT`, `INSPECTION_RESULT`, `EVIDENCE_BUNDLE` |
| `source_reference` | `VARCHAR(255)` | Indexed; UUID string of the authentic source entity |
| `deduplication_key` | `VARCHAR(255)` | Indexed; e.g. `{source_type}:{uuid}:{policy_version}` |
| `title` | `VARCHAR(255)` | Human-readable work order title |
| `description` | `TEXT` | Factual operational description |
| `priority` | `VARCHAR(20)` | Indexed; `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `status` | `VARCHAR(30)` | Indexed; `OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` |
| `recommended_action`| `TEXT` | Deterministic action guidance per policy |
| `reason` | `TEXT` | Ground truth evidence justification |
| `risk_state_at_creation` | `VARCHAR(50)` | Snapshot of risk state at drafting (`CRITICAL`, `ELEVATED`, `WATCH`) |
| `predicted_rul_at_creation` | `FLOAT` | Snapshot of estimated RUL (cycles) |
| `health_index_at_creation` | `FLOAT` | Snapshot of normalized Health Index $[0, 1]$ |
| `anomaly_score_at_creation`| `FLOAT` | Snapshot of PatchCore image anomaly distance |
| `policy_version` | `VARCHAR(50)` | Version of maintenance policy applied (`maintenance-policy-v1.0.0`) |
| `evidence_references` | `JSON` | List of typed evidence pointers |
| `created_by_id` | `UUID` | Foreign Key to `users.id` (ON DELETE SET NULL) |
| `assigned_to_id`| `UUID` | Foreign Key to `users.id` (ON DELETE SET NULL) |
| `created_at` | `TIMESTAMPTZ` | Timestamp when work order was drafted |
| `acknowledged_at`| `TIMESTAMPTZ`| Timestamp when operator acknowledged triage |
| `started_at` | `TIMESTAMPTZ` | Timestamp when physical execution commenced |
| `completed_at` | `TIMESTAMPTZ` | Timestamp when outcome was recorded |
| `cancelled_at` | `TIMESTAMPTZ` | Timestamp when cancelled with reason |
| `updated_at` | `TIMESTAMPTZ` | Timestamp of last modification |
| `resolution_notes` | `TEXT` | Human-recorded outcome notes or cancellation reason |

Composite Indexes:
- `ix_maintenance_domain_status`: (`source_domain`, `status`)
- `ix_maintenance_machine_status`: (`machine_id`, `status`)

### Table: `maintenance_events`
Immutable append-only audit event history tracking every state mutation and operator comment.

| Column | Type | Constraints / Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `work_order_id` | `UUID` | Foreign Key to `maintenance_work_orders.id` (CASCADE) |
| `event_type` | `VARCHAR(50)` | `CREATED`, `ACKNOWLEDGED`, `STARTED`, `COMPLETED`, `CANCELLED` |
| `from_status` | `VARCHAR(30)` | Previous status (`OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`, etc.) |
| `to_status` | `VARCHAR(30)` | New status |
| `actor_id` | `UUID` | Foreign Key to `users.id` (ON DELETE SET NULL) |
| `notes` | `TEXT` | Operator remarks or resolution details |
| `event_metadata`| `JSON` | Context snapshot (policy, assignments, reasons) |
| `created_at` | `TIMESTAMPTZ` | Immutable event timestamp |

---

## 3. Strict Domain Separation

In accordance with MachIntel foundational rules:
- **MACHINE_HEALTH:** Recommendations derived exclusively from NASA C-MAPSS FD001 run-to-failure telemetry, RUL regressions, and analytical risk assessments.
- **VISUAL_INSPECTION:** Recommendations derived exclusively from MVTec AD `metal_nut` PatchCore image anomaly detections.
- **No Physical Cross-Inference:** MachIntel never correlates visual defects on metal nuts with turbofan turbine degradation. The two domains maintain strictly segregated evidence models, tables, and work orders.
