# M12 Reliability & Fault Tolerance

## Concurrency Control

MachIntel eliminates concurrency hazards through PostgreSQL transactional isolation:

1. **Row-Level Exclusion**: Workers claim pending tasks using `FOR UPDATE SKIP LOCKED`. This guarantees that even if multiple worker processes poll concurrently, each pending job is locked by exactly one transaction and claimed by one worker.
2. **Execution Key Uniqueness**: The database table enforces a unique partial index on `(execution_key)` where `status IN ('QUEUED', 'RUNNING')`. Attempting to enqueue an identical job while one is currently in progress automatically resolves to the existing active job rather than creating duplicates.
3. **No In-Memory Dependencies**: Locking is entirely database-backed; multiple worker processes on the same or separate machines operate without shared memory locks.

---

## Retry Strategy & Error Classification

Jobs are configured with bounded retries (`max_attempts`, default 3). Errors are classified into two categories:

### 1. Transient Failures (Retryable)
- Database connection hiccups or temporary lock contentions.
- Handled by incrementing `attempt_count`, recording the error message, transitioning status to `RETRYING`, and applying exponential backoff ($2^{\text{attempt}} \times \text{delay}$).
- If `attempt_count >= max_attempts`, the job transitions permanently to `FAILED`.

### 2. Permanent Failures (Non-Retryable)
- Invalid job parameters or unparseable payloads (`INVALID_PAYLOAD`).
- Entity not found (`ENTITY_NOT_FOUND`).
- Unsupported job types (`UNKNOWN_JOB_TYPE`).
- These immediately transition to `FAILED` without burning retry attempts.

---

## Stale Lease Recovery (Reaper)

To prevent orphaned jobs if a worker process crashes abruptly or is killed via `SIGKILL`:

1. **Active Heartbeats**: Every active worker process periodically writes a heartbeat to `worker_heartbeats` every 5 seconds and updates the job's `heartbeat_at` timestamp.
2. **Reaper Mechanism**: The worker runs a periodic recovery scan:
   ```sql
   SELECT * FROM background_jobs
   WHERE status = 'RUNNING'
     AND heartbeat_at < NOW() - INTERVAL '120 seconds'
   ```
3. **Recovery Action**:
   - If `attempt_count < max_attempts`: status is reset to `RETRYING` so healthy workers can claim it.
   - If `attempt_count >= max_attempts`: status is set to `FAILED` with error code `WORKER_TIMEOUT_EXCEEDED`.

---

## Graceful Worker Shutdown

When a worker receives `SIGINT` (Ctrl+C) or `SIGTERM` (Docker stop):
1. The running flag `self._running` is set to `False`.
2. The polling loop ceases claiming new work from `background_jobs`.
3. The currently executing job is allowed to complete or its transaction rolled back cleanly.
4. The worker unregisters itself from `worker_heartbeats`.
5. Database engine pools are disposed cleanly.
