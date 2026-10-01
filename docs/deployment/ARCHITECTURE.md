# M13 Local Production Stack Architecture

## Topology Overview

The MachIntel local production deployment is organized into four distinct services running across an isolated Docker network (`machintel_default`) or locally on the host network.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Network                          │
│                                                                        │
│  ┌───────────────────────┐                  ┌───────────────────────┐  │
│  │   machintel_frontend  │                  │   machintel_worker    │  │
│  │   Image: node:22      │                  │   Image: python:3.13  │  │
│  │   Port: 3000:3000     │                  │   Ports: NONE (0)     │  │
│  │   User: nextjs (1001) │                  │   User: machintel     │  │
│  └───────────┬───────────┘                  └───────────┬───────────┘  │
│              │                                          │              │
│              │ (HTTP REST / SSE)                        │ (FOR UPDATE  │
│              ▼                                          │  SKIP LOCKED)│
│  ┌───────────────────────┐                              │              │
│  │   machintel_backend   │                              │              │
│  │   Image: python:3.13  │                              │              │
│  │   Port: 8000:8000     │                              │              │
│  │   User: machintel     │                              │              │
│  └───────────┬───────────┘                              │              │
│              │                                          │              │
│              │ (ACID Migrations / Queries)              │              │
│              ▼                                          ▼              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        machintel_postgres                        │  │
│  │                        Image: postgres:16-alpine                 │  │
│  │                        Port: 5432:5432                           │  │
│  │                        Volume: postgres_data                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Service Responsibilities & Contracts

### 1. `machintel_postgres` (Data Store)
- **Role**: Authoritative ACID relational database storing machines, cycle telemetry, predictions, risk assessments, alerts, evidence records, maintenance work orders, AI investigation audits, background jobs, and worker heartbeats.
- **Health Check**: `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` every 5s.
- **Persistence**: Backed by named volume `postgres_data` mapping to `/var/lib/postgresql/data`. Data survives container recreation.

### 2. `machintel_backend` (API Server)
- **Role**: FastAPI application serving typed JSON REST endpoints and Server-Sent Events (SSE).
- **Startup Order**: Starts strictly after `postgres` becomes healthy.
- **Migration Ownership**: Serves as the single migration owner. Runs `alembic upgrade head` on container entry before binding uvicorn to port 8000.
- **Health Check**: Probes `/api/v1/health/liveness` every 10s.

### 3. `machintel_worker` (Background Daemon)
- **Role**: Dedicated Python process (`python -m backend.app.worker.worker`) executing operational background intelligence materializations (`EVIDENCE_REFRESH`, `RISK_REFRESH`, `MAINTENANCE_RECOMMENDATION_REFRESH`, `ANALYTICS_REFRESH`).
- **Startup Order**: Starts after `postgres` and `backend` are healthy, guaranteeing schema migrations have completed.
- **Network Exposure**: **Zero exposed public ports**. Interacts with the system purely via database connection pools and shared volumes.

### 4. `machintel_frontend` (Command Center UI)
- **Role**: Next.js 15 production server rendering the industrial command center, machine telemetry studio, alert triage queue, visual inspection station, evidence workspace, maintenance workflow, and job monitor console.
- **Startup Order**: Starts after `backend` is healthy.
- **Exposure**: Binds port 3000 on the host network.

---

## Storage & Artifact Mounts

| Host Path | Container Path | Purpose | Persistence Mode |
|---|---|---|---|
| Named volume `postgres_data` | `/var/lib/postgresql/data` | PostgreSQL database files | Named Docker Volume |
| `./storage/` | `/app/storage/` | Inspection images, anomaly heatmaps, trained models, database backups | Host Bind Mount |
| `./data/` | `/app/data/` | Raw C-MAPSS FD001 and MVTec AD datasets | Host Bind Mount |
| `./backend/` | `/app/backend/` | Application codebase | Host Bind Mount |
