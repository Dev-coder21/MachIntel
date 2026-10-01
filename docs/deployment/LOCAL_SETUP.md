# Local Setup Guide

This guide covers getting a fresh clone of MachIntel running locally, both via **Docker Compose** (recommended for containerized local production) and **Native Execution** (recommended for local development).

---

## Prerequisites

- **Git**: 2.30+
- **Python**: 3.11, 3.12, or 3.13
- **Node.js**: 20 or 22+ with `npm`
- **PostgreSQL**: 16+ (if running natively)
- **Docker & Docker Compose**: (if running containerized)

---

## Workflow A: Docker Compose (Local Production Stack)

### 1. Clone Repository & Configure Environment
```bash
git clone https://github.com/organization/MachIntel.git
cd MachIntel

# Copy configuration template
cp .env.example .env
```

### 2. Build and Launch Containers
```bash
# Build production images and start all 4 services
make build
make up

# Alternatively:
docker compose up -d --build
```

### 3. Verify Stack Health
```bash
make status
# Or: ./scripts/verify_stack.sh
```

### 4. Create Initial Administrator Account
```bash
# Run interactive bootstrap within the running backend container
docker compose exec backend python backend/scripts/create_first_admin.py
```

### 5. Access Platforms
- **Command Center UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Health Diagnostics**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## Workflow B: Native Local Execution

### 1. Database Setup
Ensure local PostgreSQL 16 is running on port 5432:
```bash
createdb machintel
```

### 2. Backend Virtualenv & Dependencies
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations to single head
alembic -c alembic.ini upgrade head
```

### 3. Ingest Authoritative Datasets
```bash
# Ingest official NASA C-MAPSS FD001 run-to-failure cycles
python scripts/ingest_cmapss.py

# Materialize initial evidence
python scripts/materialize_evidence.py

# Create system administrator account
python scripts/create_first_admin.py
```

### 4. Launch Services in Separate Terminals

**Terminal 1 — FastAPI Backend**:
```bash
source backend/.venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Background Worker Daemon**:
```bash
source backend/.venv/bin/activate
python -m backend.app.worker.worker
```

**Terminal 3 — Next.js Frontend**:
```bash
cd frontend
npm install
npm run dev
```

---

## Stopping the Services

```bash
# For Docker Compose:
make down
# Or: docker compose down

# For Native:
pkill -f "python -m backend.app.worker.worker"
pkill -f "uvicorn backend.app.main:app"
```
