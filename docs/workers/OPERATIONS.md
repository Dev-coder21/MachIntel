# M12 Worker Operations & Management

## Local Process Execution

To execute the background worker daemon locally:

```bash
# Activate virtual environment
cd /Users/devtrivedi/Desktop/MachIntel/backend
source .venv/bin/activate

# Launch worker
python -m backend.app.worker.worker
```

Example startup logs:
```
2026-10-01 19:15:00 [INFO] worker: Starting MachIntel Worker daemon (ID: worker-a81f3b20, PID: 34120)
2026-10-01 19:15:00 [INFO] worker: Database connectivity verified. Worker heartbeat registered.
2026-10-01 19:15:00 [INFO] worker: Periodic scheduler enabled. Registered 4 job definitions.
2026-10-01 19:15:00 [INFO] worker: Entering job processing loop (poll interval: 2.0s)...
```

---

## Docker Compose Execution

To run the entire MachIntel stack including PostgreSQL, backend, frontend, and worker:

```bash
docker compose up -d
```

To view worker logs in Docker:
```bash
docker compose logs -f worker
```

To stop the worker gracefully:
```bash
docker compose stop worker
```

---

## Operational REST APIs

All job endpoints are located under `/api/v1/jobs` and enforce JWT authentication and RBAC.

| Method | Endpoint | RBAC Roles | Description |
|---|---|---|---|
| `POST` | `/api/v1/jobs/{job_type}` | `OPERATOR`, `ADMIN` | Enqueue an on-demand operational refresh job. |
| `GET` | `/api/v1/jobs` | `VIEWER`, `OPERATOR`, `ADMIN` | List jobs with optional `status`, `job_type`, `limit`, `skip`. |
| `GET` | `/api/v1/jobs/{job_id}` | `VIEWER`, `OPERATOR`, `ADMIN` | Retrieve execution details, payload, and output summary. |
| `GET` | `/api/v1/jobs/summary` | `VIEWER`, `OPERATOR`, `ADMIN` | Aggregated metrics and last refresh timestamps. |
| `GET` | `/api/v1/jobs/health` | `VIEWER`, `OPERATOR`, `ADMIN` | Worker cluster health, active worker count, and scheduler status. |
| `GET` | `/api/v1/jobs/events` | `VIEWER`, `OPERATOR`, `ADMIN` | Server-Sent Events (SSE) stream for real-time job state transitions. |

---

## Operator UI: Job Monitor

Navigating to `/admin/jobs` in the MachIntel frontend displays the **Background Jobs & Operational Refresh** console:
- **Worker Status Banner**: Real-time heartbeat indicator, active worker count, and database ACID queue status.
- **Trigger Panel**: Dedicated buttons for `EVIDENCE_REFRESH`, `RISK_REFRESH`, `MAINTENANCE_RECOMMENDATION_REFRESH`, and `ANALYTICS_REFRESH`. (Disabled for `VIEWER` users with explicit visual indicator).
- **Execution History**: Searchable, status-filtered table with attempt counters, execution duration, and detail inspector modal.
