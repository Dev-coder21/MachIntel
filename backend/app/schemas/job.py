from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.job import JobStatus, JobType


class JobTriggerRequest(BaseModel):
    """Payload to trigger an on-demand operational background job."""
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional execution parameters or filters for the job"
    )


class JobResponse(BaseModel):
    """Full representation of a background job execution record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    status: str
    execution_key: Optional[str] = None
    requested_by_id: Optional[uuid.UUID] = None
    attempt_count: int
    max_attempts: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    output_summary: Dict[str, Any] = Field(default_factory=dict)
    retry_metadata: Dict[str, Any] = Field(default_factory=dict)
    worker_id: Optional[str] = None
    duration_ms: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """Paginated list of background jobs."""
    items: List[JobResponse]
    total: int
    skip: int
    limit: int


class JobSummaryResponse(BaseModel):
    """Fleet-wide job execution statistics and freshness overview."""
    total_jobs: int
    queued_count: int
    running_count: int
    succeeded_count: int
    failed_count: int
    cancelled_count: int
    recent_jobs: List[JobResponse]
    last_refresh_by_type: Dict[str, Optional[datetime]]
    active_workers_count: int


class WorkerHeartbeatResponse(BaseModel):
    """Health and status of an individual worker process."""
    model_config = ConfigDict(from_attributes=True)

    worker_id: str
    hostname: str
    pid: int
    status: str
    started_at: datetime
    heartbeat_at: datetime
    current_job_id: Optional[uuid.UUID] = None
    metadata_info: Dict[str, Any] = Field(default_factory=dict)


class WorkerHealthResponse(BaseModel):
    """Overall background worker system health probe response."""
    status: str
    worker_enabled: bool
    scheduler_enabled: bool
    database_connected: bool
    active_workers_count: int
    active_workers: List[WorkerHeartbeatResponse]
    timestamp: datetime


class JobEventPayload(BaseModel):
    """Typed Server-Sent Event (SSE) schema for real-time operational notifications."""
    event_id: str
    event_type: str
    job_id: str
    job_type: str
    status: str
    timestamp: datetime
    summary: Optional[str] = None
    output_summary: Optional[Dict[str, Any]] = None
