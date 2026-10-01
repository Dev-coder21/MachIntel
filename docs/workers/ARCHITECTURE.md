# M12 Worker & Infrastructure Architecture

## Architecture Overview

MachIntel's background execution architecture relies on a lean, database-backed transactional queue design. Rather than introducing external queue brokers (Redis, RabbitMQ, Celery), M12 uses PostgreSQL as the single source of truth for both authoritative business records and task execution state.

```
┌────────────────────────────────────────────────────────┐
│                   MachIntel Cluster                    │
│                                                        │
│  ┌────────────────────┐       ┌─────────────────────┐  │
│  │    FastAPI API     │       │    Worker Process   │  │
│  │                    │       │                     │  │
│  │  - POST /jobs/{type}│       │  - Polling Loop     │  │
│  │  - GET /jobs       │       │  - Scheduler Loop   │  │
│  │  - GET /jobs/health│       │  - Heartbeat Loop   │  │
│  │  - GET /jobs/events│       │  - Stale Reaper     │  │
│  └─────────┬──────────┘       └──────────┬──────────┘  │
│            │                             │             │
│            │  (ACID Enqueue)             │  (Lock &    │
│            │                             │   Execute)  │
│            ▼                             ▼             │
│  ┌──────────────────────────────────────────────────┐  │
│  │              PostgreSQL 16 Engine                │  │
│  │                                                  │  │
│  │  - background_jobs (FOR UPDATE SKIP LOCKED)      │  │
│  │  - worker_heartbeats (Liveness Registry)         │  │
│  │  - Authoritative Domain Records (C-MAPSS/MVTec)  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Database Job Queue (`background_jobs`)
- **Queue Engine**: Uses PostgreSQL table `background_jobs` with row-level locking.
- **Atomicity**: Job retrieval executes via `SELECT ... WHERE status IN ('QUEUED', 'RETRYING') ORDER BY created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1`. This guarantees that across $N$ concurrent worker processes, no two workers can claim or execute the same job.
- **State Machine**:
  - `QUEUED`: Enqueued and waiting for an available worker slot.
  - `RUNNING`: Claimed by a worker; lease heartbeat continuously refreshed.
  - `SUCCEEDED`: Job finished without errors; output summary saved.
  - `RETRYING`: Transient error occurred; backoff delay active before next attempt.
  - `FAILED`: Exhausted maximum retry attempts or encountered permanent validation failure.
  - `CANCELLED`: Manually revoked before completion.

### 2. Worker Process (`backend.app.worker.worker`)
- **Process Model**: A dedicated, independent Python runtime executing outside the FastAPI web server processes.
- **Signal Handling**: Registers `SIGTERM` and `SIGINT` handlers. When signaled, the worker immediately ceases claiming new jobs, allows currently active work units to either complete or roll back safely, records a shutdown log, and disconnects gracefully from PostgreSQL.
- **Heartbeat Thread**: Periodically updates its assigned record in `worker_heartbeats` every 5 seconds, recording `hostname`, `pid`, `current_job_id`, and `heartbeat_at`.
- **Stale Job Reaper**: Periodically scans `background_jobs` for jobs marked `RUNNING` whose heartbeat has lapsed beyond `WORKER_STALE_JOB_TIMEOUT_SECONDS` (120s default). If found, the job is re-queued for retry or failed if retry limits are exceeded.

### 3. Periodic Scheduler Loop
- Runs concurrently inside the worker daemon when `SCHEDULER_ENABLED=true`.
- Periodically checks elapsed intervals for registered system jobs:
  - `EVIDENCE_REFRESH`: Every 300s (5m)
  - `RISK_REFRESH`: Every 180s (3m)
  - `MAINTENANCE_RECOMMENDATION_REFRESH`: Every 300s (5m)
  - `ANALYTICS_REFRESH`: Every 600s (10m)
- Uses `execution_key` idempotency to ensure that if a previous cycle's job is still queued or running, no duplicate job is spawned.

### 4. Event Streaming (`/api/v1/jobs/events`)
- Employs an in-memory asynchronous pub/sub broadcaster (`JobEventBroadcaster`) mounted in FastAPI.
- Transmits typed Server-Sent Events (SSE) formatted as `data: {"event_id": ..., "event_type": ..., "job_id": ...}` for instant UI reactivity without high-frequency polling.
- Clients that disconnect or do not support SSE fall back to client-side periodic polling (8s interval).
