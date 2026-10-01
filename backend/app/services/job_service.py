import asyncio
from datetime import datetime, timedelta, timezone
import json
import socket
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple
import uuid
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.errors import ConflictException, NotFoundException, ValidationException
from backend.app.core.logging import logger
from backend.app.models.job import BackgroundJob, JobStatus, JobType, WorkerHeartbeat
from backend.app.models.user import User
from backend.app.schemas.job import (
    JobEventPayload,
    JobListResponse,
    JobResponse,
    JobSummaryResponse,
    WorkerHealthResponse,
    WorkerHeartbeatResponse,
)
from backend.app.worker.handlers import JOB_HANDLERS


class JobEventBroadcaster:
    """
    Lightweight, thread-safe in-process event broadcaster for Server-Sent Events (SSE).
    Subscribers receive typed JSON events when background jobs change state.
    """
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers.discard(q)

    def publish(self, event: JobEventPayload):
        dead_queues = set()
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.add(q)
        for dq in dead_queues:
            self._subscribers.discard(dq)


event_broadcaster = JobEventBroadcaster()


class JobService:
    """
    Service governing background job lifecycle, concurrency locking,
    idempotency enforcement, worker heartbeats, and status queries.
    """

    def __init__(self, db: Session):
        self.db = db

    def trigger_job(
        self,
        job_type: str,
        payload: Optional[Dict[str, Any]] = None,
        requested_by: Optional[User] = None,
        execution_key: Optional[str] = None,
    ) -> Tuple[BackgroundJob, bool]:
        """
        Creates or returns an existing active job enforcing idempotency.
        Returns (job, is_new: bool).
        """
        if job_type not in JOB_HANDLERS:
            raise ValidationException(
                f"Unsupported job type '{job_type}'. Supported: {list(JOB_HANDLERS.keys())}"
            )

        payload_data = payload or {}
        # Auto-generate deterministic execution key if not explicitly given
        if not execution_key:
            target_key = payload_data.get("machine_id", "fleet")
            execution_key = f"{job_type}:{target_key}"

        # 1. Idempotency Check: find existing QUEUED or RUNNING job with this execution_key
        existing_active = self.db.execute(
            select(BackgroundJob).where(
                BackgroundJob.execution_key == execution_key,
                BackgroundJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
            )
        ).scalar_one_or_none()

        if existing_active:
            logger.info(
                f"Job with key '{execution_key}' is already active ({existing_active.status}). "
                f"Returning existing job {existing_active.id}."
            )
            return existing_active, False

        # 2. Create new QUEUED job
        new_job = BackgroundJob(
            id=uuid.uuid4(),
            job_type=job_type,
            status=JobStatus.QUEUED.value,
            execution_key=execution_key,
            requested_by_id=requested_by.id if requested_by else None,
            attempt_count=0,
            max_attempts=settings.WORKER_MAX_RETRIES,
            payload=payload_data,
            output_summary={},
            retry_metadata={},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(new_job)
        self.db.commit()
        self.db.refresh(new_job)

        # Broadcast SSE event
        event_broadcaster.publish(
            JobEventPayload(
                event_id=str(uuid.uuid4()),
                event_type="job_queued",
                job_id=str(new_job.id),
                job_type=new_job.job_type,
                status=new_job.status,
                timestamp=new_job.created_at,
                summary=f"Job {new_job.job_type} queued for execution",
            )
        )

        return new_job, True

    def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> JobListResponse:
        """Returns paginated list of background jobs with optional status/type filtering."""
        stmt = select(BackgroundJob)
        if status:
            stmt = stmt.where(BackgroundJob.status == status)
        if job_type:
            stmt = stmt.where(BackgroundJob.job_type == job_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = stmt.order_by(BackgroundJob.created_at.desc()).offset(skip).limit(limit)
        items = list(self.db.execute(stmt).scalars().all())

        return JobListResponse(
            items=[JobResponse.model_validate(j) for j in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_job(self, job_id: uuid.UUID) -> BackgroundJob:
        """Retrieves a single job or raises 404."""
        job = self.db.get(BackgroundJob, job_id)
        if not job:
            raise NotFoundException(f"Job '{job_id}' not found.")
        return job

    def get_summary(self) -> JobSummaryResponse:
        """Aggregates execution metrics, active worker counts, and freshness timestamps."""
        total = self.db.scalar(select(func.count(BackgroundJob.id))) or 0
        queued = self.db.scalar(
            select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.QUEUED.value)
        ) or 0
        running = self.db.scalar(
            select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.RUNNING.value)
        ) or 0
        succeeded = self.db.scalar(
            select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.SUCCEEDED.value)
        ) or 0
        failed = self.db.scalar(
            select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.FAILED.value)
        ) or 0
        cancelled = self.db.scalar(
            select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.CANCELLED.value)
        ) or 0

        # Recent 10 jobs
        recent_stmt = (
            select(BackgroundJob)
            .order_by(BackgroundJob.created_at.desc())
            .limit(10)
        )
        recent_items = list(self.db.execute(recent_stmt).scalars().all())

        # Last refresh timestamp by job type
        last_refresh: Dict[str, Optional[datetime]] = {}
        for jt in JobType:
            stmt_last = (
                select(BackgroundJob.completed_at)
                .where(
                    BackgroundJob.job_type == jt.value,
                    BackgroundJob.status == JobStatus.SUCCEEDED.value,
                )
                .order_by(BackgroundJob.completed_at.desc())
                .limit(1)
            )
            last_dt = self.db.scalar(stmt_last)
            last_refresh[jt.value] = last_dt

        # Active workers: heartbeat within last 30 seconds
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=30)
        active_workers_count = self.db.scalar(
            select(func.count(WorkerHeartbeat.worker_id)).where(
                WorkerHeartbeat.heartbeat_at >= cutoff,
                WorkerHeartbeat.status == "ACTIVE",
            )
        ) or 0

        return JobSummaryResponse(
            total_jobs=total,
            queued_count=queued,
            running_count=running,
            succeeded_count=succeeded,
            failed_count=failed,
            cancelled_count=cancelled,
            recent_jobs=[JobResponse.model_validate(j) for j in recent_items],
            last_refresh_by_type=last_refresh,
            active_workers_count=active_workers_count,
        )

    def get_worker_health(self) -> WorkerHealthResponse:
        """Probes worker fleet health, heartbeat timestamps, and DB connectivity."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=30)
        workers_stmt = (
            select(WorkerHeartbeat)
            .where(WorkerHeartbeat.heartbeat_at >= cutoff)
            .order_by(WorkerHeartbeat.heartbeat_at.desc())
        )
        active_workers = list(self.db.execute(workers_stmt).scalars().all())

        status_str = "HEALTHY" if active_workers else "INACTIVE"
        if not settings.WORKER_ENABLED:
            status_str = "DISABLED"

        return WorkerHealthResponse(
            status=status_str,
            worker_enabled=settings.WORKER_ENABLED,
            scheduler_enabled=settings.SCHEDULER_ENABLED,
            database_connected=True,
            active_workers_count=len(active_workers),
            active_workers=[WorkerHeartbeatResponse.model_validate(w) for w in active_workers],
            timestamp=datetime.now(timezone.utc),
        )

    # =========================================================================
    # Worker Internal Transactional Operations
    # =========================================================================

    def claim_next_job(self, worker_id: str) -> Optional[BackgroundJob]:
        """
        Atomically claims the oldest QUEUED job using PostgreSQL 'FOR UPDATE SKIP LOCKED'.
        Transitions job to RUNNING and sets worker_id and started_at.
        """
        stmt = (
            select(BackgroundJob)
            .where(BackgroundJob.status == JobStatus.QUEUED.value)
            .order_by(BackgroundJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = self.db.execute(stmt).scalar_one_or_none()
        if not job:
            return None

        now = datetime.now(timezone.utc)
        job.status = JobStatus.RUNNING.value
        job.worker_id = worker_id
        job.started_at = now
        job.heartbeat_at = now
        job.attempt_count += 1

        self.db.commit()
        self.db.refresh(job)

        event_broadcaster.publish(
            JobEventPayload(
                event_id=str(uuid.uuid4()),
                event_type="job_started",
                job_id=str(job.id),
                job_type=job.job_type,
                status=job.status,
                timestamp=now,
                summary=f"Job {job.job_type} claimed by {worker_id}",
            )
        )
        return job

    def heartbeat_job(self, job_id: uuid.UUID, worker_id: str):
        """Updates heartbeat on the running job and worker registry."""
        now = datetime.now(timezone.utc)
        job = self.db.get(BackgroundJob, job_id)
        if job and job.status == JobStatus.RUNNING.value and job.worker_id == worker_id:
            job.heartbeat_at = now
            self.db.commit()

    def record_job_success(
        self, job_id: uuid.UUID, worker_id: str, output_summary: Dict[str, Any], duration_ms: float
    ):
        """Marks a job as SUCCEEDED with output summary and runtime metrics."""
        now = datetime.now(timezone.utc)
        job = self.db.get(BackgroundJob, job_id)
        if not job:
            return

        job.status = JobStatus.SUCCEEDED.value
        job.completed_at = now
        job.duration_ms = duration_ms
        job.output_summary = output_summary
        job.error_code = None
        job.error_message = None

        self.db.commit()

        event_broadcaster.publish(
            JobEventPayload(
                event_id=str(uuid.uuid4()),
                event_type="job_completed",
                job_id=str(job.id),
                job_type=job.job_type,
                status=job.status,
                timestamp=now,
                summary=f"Job {job.job_type} succeeded in {duration_ms:.1f}ms",
                output_summary=output_summary,
            )
        )

    def record_job_failure(
        self,
        job_id: uuid.UUID,
        worker_id: str,
        error_code: str,
        error_message: str,
        duration_ms: float,
        is_retryable: bool = True,
    ):
        """
        Handles job failure with bounded retries.
        If attempts remain and error is retryable, transitions back to QUEUED with backoff;
        otherwise marks terminal FAILED.
        """
        now = datetime.now(timezone.utc)
        job = self.db.get(BackgroundJob, job_id)
        if not job:
            return

        job.duration_ms = duration_ms
        job.error_code = error_code
        job.error_message = error_message[:1000]

        if is_retryable and job.attempt_count < job.max_attempts:
            # Requeue for retry
            job.status = JobStatus.QUEUED.value
            job.worker_id = None
            job.retry_metadata = {
                "last_failed_at": now.isoformat(),
                "last_error": error_message[:200],
                "next_retry_attempt": job.attempt_count + 1,
            }
            logger.warning(
                f"Job {job.id} failed (attempt {job.attempt_count}/{job.max_attempts}). Requeuing."
            )
            self.db.commit()

            event_broadcaster.publish(
                JobEventPayload(
                    event_id=str(uuid.uuid4()),
                    event_type="job_queued",
                    job_id=str(job.id),
                    job_type=job.job_type,
                    status=job.status,
                    timestamp=now,
                    summary=f"Job {job.job_type} failed; requeued for attempt {job.attempt_count + 1}",
                )
            )
        else:
            # Terminal failure
            job.status = JobStatus.FAILED.value
            job.completed_at = now
            logger.error(
                f"Job {job.id} failed terminally (attempts: {job.attempt_count}): {error_message}"
            )
            self.db.commit()

            event_broadcaster.publish(
                JobEventPayload(
                    event_id=str(uuid.uuid4()),
                    event_type="job_failed",
                    job_id=str(job.id),
                    job_type=job.job_type,
                    status=job.status,
                    timestamp=now,
                    summary=f"Job {job.job_type} failed: {error_code}",
                )
            )

    def recover_stale_jobs(self, timeout_seconds: float = 60.0) -> int:
        """
        Reclaims or fails jobs stuck in RUNNING whose heartbeat is older than timeout_seconds.
        Prevents dead workers from orphaning jobs permanently.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        stmt = (
            select(BackgroundJob)
            .where(
                BackgroundJob.status == JobStatus.RUNNING.value,
                or_(
                    BackgroundJob.heartbeat_at < cutoff,
                    BackgroundJob.heartbeat_at.is_(None),
                ),
            )
            .with_for_update(skip_locked=True)
        )
        stale_jobs = list(self.db.execute(stmt).scalars().all())
        recovered_count = 0

        for job in stale_jobs:
            logger.warning(
                f"Recovering stale RUNNING job {job.id} (worker: {job.worker_id}, last heartbeat: {job.heartbeat_at})"
            )
            if job.attempt_count < job.max_attempts:
                job.status = JobStatus.QUEUED.value
                job.worker_id = None
                job.retry_metadata = {
                    "stale_recovery_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "Worker heartbeat timed out",
                }
            else:
                job.status = JobStatus.FAILED.value
                job.completed_at = datetime.now(timezone.utc)
                job.error_code = "WORKER_TIMEOUT"
                job.error_message = "Worker heartbeat timed out and max attempts reached"
            recovered_count += 1

        if recovered_count > 0:
            self.db.commit()

        return recovered_count

    def update_worker_heartbeat(
        self,
        worker_id: str,
        hostname: str,
        pid: int,
        status: str = "ACTIVE",
        current_job_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Registers or refreshes heartbeat entry in worker_heartbeats table."""
        now = datetime.now(timezone.utc)
        record = self.db.get(WorkerHeartbeat, worker_id)
        if not record:
            record = WorkerHeartbeat(
                worker_id=worker_id,
                hostname=hostname,
                pid=pid,
                status=status,
                started_at=now,
                heartbeat_at=now,
                current_job_id=current_job_id,
                metadata_info=metadata or {},
            )
            self.db.add(record)
        else:
            record.status = status
            record.heartbeat_at = now
            record.current_job_id = current_job_id
            if metadata:
                record.metadata_info = metadata
        self.db.commit()
