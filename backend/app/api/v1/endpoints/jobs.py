import asyncio
from datetime import datetime, timezone
import json
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.job import JobStatus, JobType
from backend.app.models.user import User, UserRole
from backend.app.schemas.job import (
    JobEventPayload,
    JobListResponse,
    JobResponse,
    JobSummaryResponse,
    JobTriggerRequest,
    WorkerHealthResponse,
)
from backend.app.services.job_service import JobService, event_broadcaster

router = APIRouter(prefix="/jobs", tags=["Background Jobs & Operational Refresh"])


@router.post(
    "/{job_type}",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an on-demand operational background job (Operator/Admin)",
)
def trigger_job(
    job_type: str,
    req: JobTriggerRequest = JobTriggerRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> JobResponse:
    """
    Enqueues a supported operational job type (EVIDENCE_REFRESH, RISK_REFRESH,
    MAINTENANCE_RECOMMENDATION_REFRESH, ANALYTICS_REFRESH).
    Enforces idempotency: returning existing active job if currently QUEUED or RUNNING.
    """
    svc = JobService(db)
    job, is_new = svc.trigger_job(
        job_type=job_type,
        payload=req.payload,
        requested_by=current_user,
    )
    return JobResponse.model_validate(job)


@router.get(
    "/summary",
    response_model=JobSummaryResponse,
    summary="Get fleet background job execution statistics and data freshness",
)
def get_job_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobSummaryResponse:
    """Returns job counts by status, last refresh timestamps, and active worker count."""
    svc = JobService(db)
    return svc.get_summary()


@router.get(
    "/health",
    response_model=WorkerHealthResponse,
    summary="Get background worker process health and active heartbeats",
)
def get_worker_health(
    db: Session = Depends(get_db),
) -> WorkerHealthResponse:
    """Probe checking worker fleet liveness, heartbeats, and database reachability."""
    svc = JobService(db)
    return svc.get_worker_health()


@router.get(
    "/events",
    summary="Server-Sent Events (SSE) stream for real-time background job updates",
)
async def stream_job_events(
    max_events: Optional[int] = Query(None, description="Max events to stream before closing (useful for testing)"),
    current_user: User = Depends(get_current_user),
):
    """
    Streams Server-Sent Events (SSE) emitting typed JobEventPayload JSON objects
    as background tasks transition between QUEUED, RUNNING, SUCCEEDED, and FAILED.
    """
    queue = event_broadcaster.subscribe()

    async def event_generator():
        sent_count = 0
        try:
            # Emit initial connection handshake event
            init_event = {
                "event_id": str(uuid.uuid4()),
                "event_type": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": "Connected to MachIntel job event stream",
            }
            yield f"data: {json.dumps(init_event)}\n\n"
            sent_count += 1
            if max_events is not None and sent_count >= max_events:
                return

            while True:
                try:
                    # Wait up to 15s for an event, then send heartbeat comment
                    event: JobEventPayload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {event.model_dump_json()}\n\n"
                    sent_count += 1
                    if max_events is not None and sent_count >= max_events:
                        return
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield f": keepalive {datetime.now(timezone.utc).isoformat()}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "",
    response_model=JobListResponse,
    summary="List background jobs with filtering and pagination",
)
def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status (QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED)"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobListResponse:
    """Returns paginated background job execution history."""
    svc = JobService(db)
    return svc.list_jobs(status=status, job_type=job_type, skip=skip, limit=limit)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get detailed record and execution metadata for a specific job",
)
def get_job_detail(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Retrieves full execution summary, errors, and metadata for a job."""
    svc = JobService(db)
    job = svc.get_job(job_id)
    return JobResponse.model_validate(job)
