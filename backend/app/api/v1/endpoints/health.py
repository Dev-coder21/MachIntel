import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.health import DatabaseHealthResponse, HealthResponse

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("", response_model=HealthResponse, summary="Application General Health Check")
@router.get("/liveness", response_model=HealthResponse, summary="Application Liveness Probe")
def get_health() -> HealthResponse:
    """Return application operational status, active version, and timestamp."""
    return HealthResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/db", response_model=DatabaseHealthResponse, summary="PostgreSQL Connectivity Check")
@router.get("/readiness", response_model=DatabaseHealthResponse, summary="Application Readiness Probe")
def get_db_health(db: Session = Depends(get_db)) -> DatabaseHealthResponse:
    """Execute a lightweight SELECT 1 query to verify live PostgreSQL connection health."""
    start_time = time.perf_counter()
    try:
        result = db.execute(text("SELECT 1;")).scalar()
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        if result == 1:
            return DatabaseHealthResponse(
                status="healthy",
                database="connected",
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc),
            )
        else:
            return DatabaseHealthResponse(
                status="degraded",
                database="connected",
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc),
                error="Unexpected response from database check query",
            )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"Database health check failed: {str(exc)}", exc_info=True)
        err_msg = str(exc) if settings.ENVIRONMENT != "production" else "Database connectivity check failed"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=DatabaseHealthResponse(
                status="unhealthy",
                database="disconnected",
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc),
                error=err_msg,
            ).model_dump(mode="json"),
        )
