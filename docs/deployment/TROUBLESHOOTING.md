# Deployment Troubleshooting Guide

This guide details common operational failure modes, diagnostic recipes, and recovery actions for MachIntel.

---

## 1. Port 8000 Already in Use

### Symptom
`uvicorn` fails to start with:
`[Errno 48] Address already in use` or returns unexpected `404` for MachIntel routes.

### Diagnosis
Check which process is listening on port 8000:
```bash
lsof -i :8000
```

### Resolution
Identify the PID and terminate the stale process:
```bash
kill -9 <PID>
```
Or change the port in `.env` and `docker-compose.yml`.

---

## 2. PostgreSQL Connection Refused

### Symptom
Backend outputs:
`sqlalchemy.exc.OperationalError: could not connect to server: Connection refused`

### Diagnosis
Verify PostgreSQL service state:
```bash
# Docker Compose:
docker compose ps postgres

# Native:
pg_isready -h localhost -p 5432
```

### Resolution
- For Docker: Ensure `postgres` service is running and healthy:
  ```bash
  docker compose up -d postgres
  ```
- For Native: Start local PostgreSQL service:
  ```bash
  brew services start postgresql@16 # macOS
  sudo systemctl start postgresql   # Linux
  ```

---

## 3. Database Migrations Out of Sync

### Symptom
API queries fail with:
`relation "background_jobs" does not exist` or `alembic Multiple heads detected`.

### Diagnosis
Check Alembic heads:
```bash
source backend/.venv/bin/activate
alembic -c backend/alembic.ini heads
alembic -c backend/alembic.ini current
```

### Resolution
Upgrade database to the single canonical head:
```bash
alembic -c backend/alembic.ini upgrade head
```

---

## 4. Background Worker Reports DEGRADED Status

### Symptom
Job Monitor UI (`/admin/jobs`) displays `DEGRADED` worker status with `0 process(es)`.

### Diagnosis
The worker process has stopped heartbeating to `worker_heartbeats`.
Inspect worker process logs:
```bash
# Docker:
docker compose logs --tail=100 worker

# Native:
ps aux | grep worker
```

### Resolution
Restart the worker process:
```bash
# Docker:
docker compose restart worker

# Native:
source backend/.venv/bin/activate
python -m backend.app.worker.worker
```

---

## 5. Next.js Production Build Fails

### Symptom
`npm run build` exits with error or type mismatch.

### Diagnosis
Run TypeScript check in isolation:
```bash
cd frontend
npx tsc --noEmit
```

### Resolution
Fix any type errors or missing dependencies, clean the Next.js cache, and rebuild:
```bash
rm -rf frontend/.next
npm run build
```
