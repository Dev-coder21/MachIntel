# AI Inspector — Audit Trail & Persistence

Every investigation performed through the AI Inspector is persisted to PostgreSQL to satisfy aerospace and industrial auditability standards.

---

## Database Schema (`ai_investigations`)

The `ai_investigations` table stores complete trace metadata for each inquiry:

| Column | Type | Constraints / Description |
|---|---|---|
| `id` | `UUID` | Primary Key (Default: `uuid4()`) |
| `user_id` | `UUID` | Foreign Key (`users.id`, `ON DELETE CASCADE`), Indexed |
| `question` | `Text` | Authenticated user's investigation prompt |
| `context` | `JSON` | Optional contextual constraints (`machine_id`, `run_id`, `domain`) |
| `status` | `String(50)` | `COMPLETED`, `FAILED`, `PROVIDER_UNAVAILABLE` (Indexed) |
| `provider` | `String(50)` | Configured provider identifier (e.g. `mock`, `openai`, `anthropic`) |
| `model` | `String(100)` | Model identifier (e.g. `gpt-4o-mini`, `claude-3-5-sonnet`) |
| `tool_calls` | `JSON` | Array of executed tools with arguments, status, duration, and citations |
| `domains_consulted` | `JSON` | List of domains queried (e.g. `["MACHINE_HEALTH"]`) |
| `evidence_ids` | `JSON` | Array of authoritative UUID evidence records cited in findings |
| `answer` | `Text` | Synthesized grounded forensic findings |
| `evidence_citations`| `JSON` | Full structured evidence citation metadata |
| `limitations` | `JSON` | Analytical uncertainty and boundary conditions |
| `execution_time_ms` | `Float` | Total orchestration duration in milliseconds |
| `error_message` | `Text` | Error description if status is `FAILED` |
| `created_at` | `DateTime(tz)` | Investigation start timestamp (Indexed) |
| `completed_at` | `DateTime(tz)` | Investigation completion timestamp |

---

## Tool Execution Trace Record

Inside the `tool_calls` JSON column, each tool invocation records:

```json
{
  "tool_name": "get_machine_health_summary",
  "arguments": { "machine_id": "TURBOFAN-ENG-001" },
  "status": "SUCCESS",
  "duration_ms": 14.8,
  "evidence_ids_returned": ["ev-rec-001", "ev-rec-002"],
  "timestamp": "2026-10-01T12:00:01.120Z"
}
```

Sensitive credentials and massive telemetry arrays are excluded from tool call audit summaries to ensure data minimization and high query performance.
