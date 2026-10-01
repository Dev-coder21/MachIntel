# Alert System & Lifecycle Specification

## Overview

The MachIntel Alert System translates deterministic risk assessments into actionable operational triage tasks. Alerts are triggered exclusively by real risk assessments; no synthetic or ungrounded alerts are ever created.

---

## Alert Data Model

Persisted in PostgreSQL table `alerts`:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique alert identifier |
| `machine_id` | String (FK) | Reference to target machine |
| `risk_assessment_id` | UUID (FK) | Reference to authoritative risk assessment record |
| `severity` | Enum | `INFO`, `WARNING`, or `CRITICAL` |
| `status` | Enum | `OPEN`, `ACKNOWLEDGED`, or `RESOLVED` |
| `title` | String | Operational summary title |
| `description` | Text | Explanatory description of risk threshold breach |
| `reason_codes` | JSONB | Array of triggered programmatic reason codes |
| `deduplication_key` | String | Hash key for deduplication (`machine:state:policy`) |
| `acknowledged_at` | DateTime (nullable)| Timestamp of triage acknowledgment |
| `acknowledged_by` | String (nullable) | User UUID who acknowledged |
| `resolved_at` | DateTime (nullable)| Timestamp of operational resolution |
| `resolved_by` | String (nullable) | User UUID who resolved |
| `created_at` | DateTime | Timestamp when alert was dispatched |

Indexes are created on `machine_id`, `status`, `severity`, `created_at`, and `deduplication_key`.

---

## Severity Mapping Rules

Alert severity maps deterministically from the evaluated risk state:

| Evaluated Risk State | Generated Severity | Trigger Policy |
| :--- | :--- | :--- |
| `NORMAL` | None | Suppressed (no alert created) |
| `WATCH` | `INFO` | Advisory monitoring; incipient degradation drift |
| `ELEVATED` | `WARNING` | Accelerated degradation; schedule inspection |
| `CRITICAL` | `CRITICAL` | Imminent end-of-life threshold; immediate operational response |

---

## Operational Alert Lifecycle

```
       +--------------------+
       |  Alert Dispatched  |
       |    Status: OPEN    |
       +--------------------+
                 |
                 | [Operator / Admin Acknowledge]
                 v
       +--------------------+
       | Alert Acknowledged |
       | Status: ACKNOWLEDGED
       +--------------------+
                 |
                 | [Operator / Admin Resolve]
                 v
       +--------------------+
       |   Alert Resolved   |
       |  Status: RESOLVED  |
       +--------------------+
```

### RBAC Permissions:
- **VIEWER**: Can read alert queues, inspect summaries, and view machine details. Cannot acknowledge or resolve alerts.
- **OPERATOR**: Full read access + can acknowledge open alerts and resolve active/acknowledged alerts.
- **ADMIN**: Full operational and governance capabilities.
