# Environment Configuration Reference

MachIntel is configured strictly through environment variables. This document catalogs all supported variables, default values, and production validation rules.

---

## Variable Reference Catalog

| Variable | Type | Default | Description | Production Rule |
|---|---|---|---|---|
| `ENVIRONMENT` | string | `development` | Runtime mode: `development`, `test`, `production`. | When `production`, activates strict validators. |
| `DEBUG` | boolean | `true` | Enables FastAPI debug traces. | **Must be `false` in production.** |
| `SECRET_KEY` | string | *dev key* | Cryptographic signing key for JWT tokens. | **Must be $\ge 32$ chars and not default in production.** |
| `ALGORITHM` | string | `HS256` | JWT signing algorithm. | Fixed to `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `1440` (24h) | JWT session expiration window. | Recommended: 480 (8h). |
| `DATABASE_URL` | string | *local url* | PostgreSQL connection string. | Required. Must include user, password, host, port, db. |
| `POSTGRES_USER` | string | `machintel_user` | PostgreSQL username (Docker). | Standard username. |
| `POSTGRES_PASSWORD` | string | `machintel_password` | PostgreSQL password (Docker). | Should be set securely in production. |
| `POSTGRES_DB` | string | `machintel` | PostgreSQL database name. | Default `machintel`. |
| `BACKEND_CORS_ORIGINS` | JSON list | `["http://localhost:3000"]` | Allowed CORS origins for browser clients. | **Wildcard `["*"]` is strictly forbidden in production.** |
| `NEXT_PUBLIC_API_URL` | string | `http://localhost:8000/api/v1` | Public API endpoint for frontend client queries. | Required by Next.js build. |
| `AI_INSPECTOR_PROVIDER` | string | `mock` | LLM provider: `mock`, `openai`, `anthropic`. | `mock` runs deterministically without external keys. |
| `AI_INSPECTOR_API_KEY` | string | `None` | API key for cloud LLM (optional). | Never commit to source control. |
| `AI_INSPECTOR_MODEL` | string | `gpt-4o` | Model name for AI Inspector investigations. | Defaults to `gpt-4o`. |
| `WORKER_ENABLED` | boolean | `true` | Master switch for background processing. | If `false`, worker stops claiming jobs. |
| `SCHEDULER_ENABLED` | boolean | `true` | Enables periodic refresh job execution. | If `false`, worker only processes manual triggers. |
| `WORKER_POLL_INTERVAL_SECONDS` | float | `2.0` | Queue polling sleep interval. | Recommended: 2–5 seconds. |
| `WORKER_HEARTBEAT_INTERVAL_SECONDS`| float | `5.0` | Worker heartbeat write frequency. | Recommended: 5 seconds. |
| `WORKER_STALE_JOB_TIMEOUT_SECONDS` | float | `120.0` | Time after which an unacknowledged job is reaped. | Recommended: 120 seconds. |
| `WORKER_MAX_ATTEMPTS` | int | `3` | Maximum retry attempts for transient job failures. | Maximum retry limit. |
| `SCHEDULE_EVIDENCE_REFRESH_INTERVAL`| int | `300` (5m) | Periodic interval for `EVIDENCE_REFRESH` (seconds). | Configurable. |
| `SCHEDULE_RISK_REFRESH_INTERVAL` | int | `180` (3m) | Periodic interval for `RISK_REFRESH` (seconds). | Configurable. |
| `SCHEDULE_MAINTENANCE_REFRESH_INTERVAL`| int | `300` (5m) | Periodic interval for maintenance refresh (seconds). | Configurable. |
| `SCHEDULE_ANALYTICS_REFRESH_INTERVAL` | int | `600` (10m) | Periodic interval for telemetry audit (seconds). | Configurable. |

---

## Production Security Validation Rules

When `ENVIRONMENT=production`, the application executes strict startup assertions in `backend/app/core/config.py`:

```python
if self.ENVIRONMENT.lower() == "production":
    if self.SECRET_KEY == "insecure-dev-secret-key-change-in-production-min-32-chars-long" or len(self.SECRET_KEY) < 32:
        raise ValueError("In production, SECRET_KEY must be an environment-configured secret of at least 32 characters.")
    if self.DEBUG:
        raise ValueError("In production, DEBUG must be set to False.")
    if "*" in self.BACKEND_CORS_ORIGINS:
        raise ValueError("In production, wildcard CORS origin ('*') is forbidden when credentials are enabled.")
```
If any of these conditions fail, the backend process immediately terminates with a descriptive error.
