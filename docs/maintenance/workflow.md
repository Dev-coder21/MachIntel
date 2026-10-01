# Maintenance Lifecycle & Workflow Transitions

## 1. Controlled State Machine

MachIntel enforces an explicit, finite state machine for all maintenance work items. Arbitrary status mutation is strictly prohibited.

```
       [ OPEN ] (Initial state upon draft creation)
          │
          ├─────────────────────────┐
          ▼                         ▼
   [ ACKNOWLEDGED ]            [ CANCELLED ] (Terminal)
          │                         ▲
          ├─────────────────────────┤
          ▼                         │
   [ IN_PROGRESS ]                  │
          │                         │
          ├─────────────────────────┘
          ▼
    [ COMPLETED ] (Terminal, requires verified outcome notes)
```

---

## 2. Transition Rules & Preconditions

| Initial State | Target State | Permitted Roles | Required Payload | Side Effects & Audits |
|---|---|---|---|---|
| None | `OPEN` | OPERATOR, ADMIN | Valid source reference UUID | - `created_at` recorded<br>- `MaintenanceEvent(CREATED)` appended<br>- `AuditLog(MAINTENANCE_WORK_ORDER_CREATED)`<br>- Evidence record `MAINTENANCE_RECOMMENDATION` registered |
| `OPEN` | `ACKNOWLEDGED` | OPERATOR, ADMIN | Optional `notes`, optional `assigned_to_id` | - `acknowledged_at` recorded<br>- `MaintenanceEvent(ACKNOWLEDGED)` appended<br>- `AuditLog(MAINTENANCE_WORK_ORDER_ACKNOWLEDGED)` |
| `ACKNOWLEDGED` | `IN_PROGRESS` | OPERATOR, ADMIN | Optional `notes` | - `started_at` recorded<br>- `MaintenanceEvent(STARTED)` appended<br>- `AuditLog(MAINTENANCE_WORK_ORDER_STARTED)` |
| `IN_PROGRESS` | `COMPLETED` | OPERATOR, ADMIN | `resolution_notes` (Min 3 characters) | - `completed_at` recorded<br>- `MaintenanceEvent(COMPLETED)` appended<br>- `AuditLog(MAINTENANCE_WORK_ORDER_COMPLETED)`<br>- `EvidenceRecord(MAINTENANCE_OUTCOME)` registered with relationship `DOCUMENTS` |
| `OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS` | `CANCELLED` | OPERATOR, ADMIN | `reason` (Min 3 characters) | - `cancelled_at` recorded<br>- `resolution_notes` prefixed with `CANCELLED:`<br>- `MaintenanceEvent(CANCELLED)` appended<br>- `AuditLog(MAINTENANCE_WORK_ORDER_CANCELLED)` |

---

## 3. Disallowed Transitions & Error Handling

Any attempt to execute an invalid transition results in an immediate **`400 Bad Request`**:
- `OPEN` $\rightarrow$ `COMPLETED`: Rejected. Work order must first be acknowledged and placed in progress.
- `OPEN` $\rightarrow$ `IN_PROGRESS`: Rejected. Work order must first be acknowledged.
- `COMPLETED` $\rightarrow$ Any State: Terminal state; further mutation is forbidden.
- `CANCELLED` $\rightarrow$ Any State: Terminal state; further mutation is forbidden.
- Empty `resolution_notes` upon completion: Rejected with validation error.
- Empty `reason` upon cancellation: Rejected with validation error.
