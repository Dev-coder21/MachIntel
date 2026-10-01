# Auditability & Traceability Specification

## Overview

Industrial compliance and mission-critical operations require complete transparency into operational state changes, threshold evaluations, and human interactions. MachIntel implements a lightweight, append-only audit trail in PostgreSQL to capture all lifecycle mutations.

---

## Audit Log Schema

Persisted in table `audit_logs`:

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID (PK) | Primary Key | Unique audit entry identifier |
| `actor_id` | String(100) | Indexed | User ID or system service identifier |
| `actor_email` | String(255)| Indexed | Email address of actor |
| `action` | String(100) | Indexed | Action identifier (e.g. `ALERT_ACKNOWLEDGE`, `ALERT_RESOLVE`, `RISK_EVALUATION`) |
| `target_type` | String(50) | Indexed | Target entity type (`ALERT`, `RISK_ASSESSMENT`, `PREDICTION`) |
| `target_id` | String(100) | Indexed | Target entity UUID |
| `details` | JSONB | Nullable | Context dictionary (e.g. operational note, previous status, evaluated risk state) |
| `created_at` | DateTime | Indexed, UTC | Timestamp when mutation took place |

---

## Audited Operational Actions

The following events trigger mandatory audit log entries:

1. **`ALERT_ACKNOWLEDGE`**:
   - Actor: Operator or Admin user
   - Target: `ALERT` (`alert_id`)
   - Details: `previous_status`, `new_status`, optional operator triage note.
2. **`ALERT_RESOLVE`**:
   - Actor: Operator or Admin user
   - Target: `ALERT` (`alert_id`)
   - Details: `previous_status`, `new_status`, optional resolution comment.
3. **`RISK_EVALUATION`**:
   - Actor: Requesting user (or `SYSTEM` during automated fleet ingestion/evaluation)
   - Target: `RISK_ASSESSMENT` (`assessment_id`)
   - Details: `machine_id`, `risk_state`, `health_index`, `predicted_rul`, `policy_version`.

---

## Immutability & Retention

- Audit records are append-only.
- Updates (`UPDATE`) and deletions (`DELETE`) on the `audit_logs` table are strictly prohibited in application logic.
- Time fields use UTC timezone timestamps (`datetime.utcnow()`).
