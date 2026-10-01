# MachIntel M13 — Local Production Packaging & Deployment

## Overview

Milestone M13 establishes the local production packaging, containerization, and deployment infrastructure for MachIntel. It transforms the verified M0–M12 application into a cohesive, reproducible local stack capable of deterministic startup, zero-downtime execution, database backup/recovery, and scripted demonstration.

> **CRITICAL ARCHITECTURAL BOUNDARY:**  
> In accordance with project requirements, **cloud deployment is explicitly out of scope**. MachIntel is intentionally engineered for local on-premises execution via native system processes and containerized Docker Compose runtimes. No cloud resources (AWS, Azure, GCP, Kubernetes, or cloud queues) are utilized.

---

## Local Production Stack Architecture

The production-like stack consists of four decoupled services:

```
┌─────────────────────────────────────────────────────────────┐
│                      MachIntel Stack                        │
│                                                             │
│   ┌──────────────────┐             ┌─────────────────────┐  │
│   │ Next.js Frontend │             │ Background Worker   │  │
│   │ Port: 3000       │             │ Zero Public Ports   │  │
│   │ (Non-root user)  │             │ (Dedicated daemon)  │  │
│   └─────────┬────────┘             └──────────┬──────────┘  │
│             │                                 │             │
│             ▼                                 ▼             │
│   ┌──────────────────┐             ┌─────────────────────┐  │
│   │ FastAPI Backend  │             │ PostgreSQL 16       │  │
│   │ Port: 8000       ├────────────►│ Port: 5432 (local)  │  │
│   │ (Single Migrator)│             │ (ACID volume mount) │  │
│   └──────────────────┘             └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Packaging Components

1. **Deterministic Database Initialization**:
   - Single migration owner: The backend container/entrypoint checks database connection readiness, applies pending Alembic migrations (`alembic upgrade head`), and starts the API.
   - Worker and frontend services depend on `backend: condition: service_healthy`, preventing race conditions or premature queue polling.

2. **Hardened Multi-Stage Container Images**:
   - `backend/Dockerfile`: Built on `python:3.13-slim` with system build tools, non-root user `machintel` (UID 10001), unified entrypoint script, and zero baked secrets.
   - `frontend/Dockerfile`: Multi-stage build (`deps` $\rightarrow$ `builder` $\rightarrow$ `runner`) on `node:22-alpine` with non-root user `nextjs` (UID 1001) and production Next.js runtime.

3. **Storage & Model Artifact Persistence**:
   - Large training datasets (`data/raw/cmapss`, `data/raw/mvtec_ad`) and model artifacts (`storage/models/rul`, `storage/models/cv`) are volume-mounted rather than copied into image layers, maintaining lean images and instant rebuilds.
   - Database persistence via named Docker volume `postgres_data` or native PostgreSQL instance.

4. **One-Command Automation**:
   - Root `Makefile` provides standardized targets (`make up`, `make down`, `make status`, `make migrate`, `make test`, `make backup`, `make reset`).
   - Safe operational scripts in `scripts/` with confirmation gates for destructive tasks.

---

## Documentation Index

- [ARCHITECTURE.md](ARCHITECTURE.md) — Container topology, network exposure, and process lifecycle.
- [LOCAL_SETUP.md](LOCAL_SETUP.md) — Step-by-step installation for Docker Compose and native execution.
- [ENVIRONMENT.md](ENVIRONMENT.md) — Detailed environment variable reference and production rules.
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common failure modes, recovery recipes, and diagnostics.
- [BACKUP_RESTORE.md](BACKUP_RESTORE.md) — Database backup and restore procedures with validation proofs.
- [DEMO.md](DEMO.md) — Recommended 10-minute end-to-end platform demonstration script.
