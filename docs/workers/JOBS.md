# M12 Background Job Catalog

## Supported Job Types

MachIntel supports four deterministic operational background jobs. Each job reuses the exact authoritative services developed across M0–M11, preserving domain boundaries, audit lineage, and deduplication rules.

---

### 1. `EVIDENCE_REFRESH`

- **Purpose**: Materializes structured evidence items and inter-evidence relationships from persisted C-MAPSS run-to-failure records and MVTec visual inspection captures.
- **Underlying Service**: `backend.app.services.evidence_service.EvidenceService.materialize_all_evidence(db)`.
- **Default Execution Key**: `EVIDENCE_REFRESH:fleet` (or scoped by `machine_id`).
- **Idempotency Strategy**: Uses existing domain uniqueness constraints (`evidence_type`, `source_table`, `source_id`). Existing evidence items are updated or skipped, guaranteeing zero duplicate business records.
- **Output Summary**:
  ```json
  {
    "evidence_created": 400,
    "relationships_created": 396,
    "status": "COMPLETED"
  }
  ```

---

### 2. `RISK_REFRESH`

- **Purpose**: Evaluates all machines with latest persisted RUL predictions against `risk-policy-v1.0.0` rules, evaluates state transitions, and creates deterministic alerts.
- **Underlying Service**: `backend.app.services.risk_engine.RiskEngine` and `backend.app.services.alert_service.AlertService`.
- **Default Execution Key**: `RISK_REFRESH:fleet` (or scoped by `machine_id`).
- **Idempotency Strategy**: Alert deduplication ensures an alert is not duplicated if an open alert exists for the same machine and trigger condition. State transitions are strictly recorded only when an actual risk tier change occurs.
- **Output Summary**:
  ```json
  {
    "machines_evaluated": 100,
    "transitions_recorded": 2,
    "alerts_created": 1,
    "policy_version": "risk-policy-v1.0.0",
    "status": "COMPLETED"
  }
  ```

---

### 3. `MAINTENANCE_RECOMMENDATION_REFRESH`

- **Purpose**: Scans machines with active risk assessments or high visual defect scores to generate maintenance recommendations and draft work orders.
- **Underlying Service**: `backend.app.services.maintenance_service.MaintenanceService`.
- **Default Execution Key**: `MAINTENANCE_RECOMMENDATION_REFRESH:fleet` (or scoped by `machine_id`).
- **Idempotency Strategy**: Policy deduplication checks for existing active recommendations (`OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`) for the same machine and failure mode before drafting new records.
- **Output Summary**:
  ```json
  {
    "recommendations_evaluated": 4,
    "recommendations_drafted": 0,
    "deduplicated_count": 4,
    "policy_version": "maintenance-policy-v1.0.0",
    "status": "COMPLETED"
  }
  ```

---

### 4. `ANALYTICS_REFRESH`

- **Purpose**: Verifies authoritative telemetry cycle integrity and aggregations across all 200 turbofan units and 33,727 cycles without manufacturing shadow databases.
- **Underlying Service**: Direct SQL aggregations across `machines` and `telemetry_records`.
- **Default Execution Key**: `ANALYTICS_REFRESH:fleet`.
- **Idempotency Strategy**: Read-only verification and freshness confirmation. Purely idempotent.
- **Output Summary**:
  ```json
  {
    "total_machines": 200,
    "total_telemetry_cycles": 33727,
    "status": "COMPLETED"
  }
  ```

---

### 5. `INSPECTION_PROCESSING` (Documented Limitation)

- **Status**: **Not Implemented in M12**.
- **Architectural Rationale**: As established in M6/M7, visual inspection analysis is performed synchronously upon authenticated image upload via `POST /api/v1/inspections/analyze`. MachIntel does not possess an external asynchronous camera stream or hardware image queue. Therefore, per M12 Phase 4 instructions:
  > *"Inspection processing remains request/manual driven because no asynchronous image-ingestion source exists in M12."*
