# MachIntel M12 — Workers & Realtime Infrastructure

## Overview

Milestone M12 introduces reliable, deterministic background job processing and operational refresh infrastructure for MachIntel. It enables the system to safely execute periodic intelligence refresh pipelines, prevent duplicate/concurrent runs across multi-process deployments, recover from worker failures, track job states with strict auditability, and surface freshness indicators to the operator console.

---

## Architectural Principles

1. **ACID-Backed Queue**: PostgreSQL row-level locks (`SELECT ... FOR UPDATE SKIP LOCKED`) provide native transactional guarantees, eliminating the operational overhead and failure modes of Redis or external message brokers for local environments.
2. **Deterministic Domain Refreshes**: Background tasks never fabricate data or invent synthetic observations. They operate strictly upon authoritative, persisted records (C-MAPSS turbofan run-to-failure cycles and MVTec visual inspection captures).
3. **Strict Idempotency**: Every job has a deterministic execution key (`{JOB_TYPE}:{TARGET}`). Concurrent triggers for an active job return the existing active execution.
4. **Resilient Failure Recovery**: Leased jobs maintain an active heartbeat. If a worker process terminates unexpectedly, unacknowledged jobs are detected as stale and automatically rescheduled up to `max_attempts`.
5. **Role-Based Access Control**: Manual triggers are restricted to `OPERATOR` and `ADMIN` roles. Viewers have read-only visibility into job history and health.

---

## Non-Goals & Boundaries

M12 strictly implements local-first operational infrastructure:
- **No Cloud Queues**: No AWS SQS, Google Cloud Pub/Sub, Kafka, or RabbitMQ.
- **No Redis / Celery**: No extraneous cache or distributed task broker dependencies.
- **No Autonomous Machine Control**: MachIntel produces decision support intelligence; it does not control PLCs, SCADA actuators, or industrial machinery.
- **No Online Model Retraining**: M12 refreshes derived intelligence (risk assessments, evidence items, maintenance recommendations) from existing models and persisted data; it is not an automated continuous retraining or MLOps pipeline (deferred to M14).
- **No Cloud Deployment / Kubernetes**: Local runtime operates via native processes or local Docker Compose (cloud infrastructure deferred to M13).

---

## Documentation Index

- [ARCHITECTURE.md](ARCHITECTURE.md) — Comprehensive technical design of the PostgreSQL queue, worker daemon, and scheduler.
- [JOBS.md](JOBS.md) — Detailed catalog of supported background jobs, execution keys, and domain behavior.
- [RELIABILITY.md](RELIABILITY.md) — Concurrency control, retry policies, stale-lease reaping, and error handling.
- [OPERATIONS.md](OPERATIONS.md) — Operator instructions, manual triggering, CLI execution, and health monitoring.
- [REALTIME.md](REALTIME.md) — Server-Sent Events (SSE) streaming architecture, event schemas, and polling fallback.
