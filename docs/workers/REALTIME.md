# M12 Realtime Infrastructure & Event Schemas

## Realtime Architecture

To ensure operational freshness without overwhelming PostgreSQL or frontend clients, MachIntel implements a hybrid reactivity model:
1. **Server-Sent Events (SSE)** via `GET /api/v1/jobs/events` for lightweight push notifications of job state transitions.
2. **Bounded Polling Fallback** (8-second interval) to maintain fresh UI displays even when streaming connections are severed or unsupported.

---

## Event Transport: Server-Sent Events (SSE)

- **Endpoint**: `/api/v1/jobs/events`
- **Authentication**: JWT token required (`Authorization: Bearer <token>`).
- **Protocol**: Standard HTTP text/event-stream format.
- **Heartbeat / Keepalive**: Emits `: keepalive` comment every 15 seconds to prevent intermediary gateway timeouts.
- **Client Safety**: The stream publishes sanitized event payloads. No raw SQL queries, stack traces, credentials, or internal secrets are transmitted.

---

## Typed Event Schema

Each SSE message contains a JSON-serialized `JobEventPayload`:

```json
{
  "event_id": "9c1a5b82-416b-4e08-bf29-79f941e9b251",
  "event_type": "job_completed",
  "timestamp": "2026-10-01T19:30:00Z",
  "resource_type": "job",
  "resource_id": "job-3a21...-uuid",
  "safe_summary": "Job EVIDENCE_REFRESH completed successfully in 124.5 ms",
  "job_id": "job-3a21...-uuid"
}
```

### Supported Event Types

| Event Type | Trigger | Payload Summary |
|---|---|---|
| `job_started` | Worker claims job and transitions to `RUNNING`. | Job type and assigned worker ID. |
| `job_completed` | Worker successfully executes handler. | Duration and output metric summary. |
| `job_failed` | Job errors or exhausts retries. | Safe error code and high-level description. |
| `risk_updated` | Triggered when risk engine completes evaluations. | Count of machines evaluated and transitions. |
| `alert_created` | Triggered when an alert is enqueued by a job. | Machine ID and trigger rule. |

---

## Polling Safety & Fallback

In the Next.js frontend:
- Polling intervals are strictly bounded (`setInterval(fetchStatusAndJobs, 5000)` in the Job Monitor and `8000` in the Command Center).
- Timers are cleaned up on component unmount (`return () => clearInterval(interval)`).
- Multiple concurrent component instances share the unified `apiClient` without request storms.
