import asyncio
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.job import BackgroundJob, JobStatus, JobType, WorkerHeartbeat
from backend.app.models.user import UserRole
from backend.app.services.job_service import JobService
from backend.app.worker.handlers import (
    handle_analytics_refresh,
    handle_evidence_refresh,
    handle_maintenance_recommendation_refresh,
    handle_risk_refresh,
)


# ==============================================================================
# Job Model & State Transition Tests
# ==============================================================================

def test_job_model_lifecycle(db):
    """Verifies complete job record creation, attributes, and status transitions."""
    svc = JobService(db)
    job, is_new = svc.trigger_job(
        job_type=JobType.ANALYTICS_REFRESH.value,
        payload={"scope": "fleet"},
        execution_key=f"test-lifecycle-{uuid.uuid4().hex[:6]}",
    )
    assert is_new is True
    assert job.status == JobStatus.QUEUED.value
    assert job.attempt_count == 0
    assert job.max_attempts == settings.WORKER_MAX_RETRIES

    # Atomic claim
    claimed = svc.claim_next_job(worker_id="test-worker-1")
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == JobStatus.RUNNING.value
    assert claimed.worker_id == "test-worker-1"
    assert claimed.attempt_count == 1
    assert claimed.started_at is not None

    # Heartbeat
    svc.heartbeat_job(claimed.id, "test-worker-1")
    db.refresh(claimed)
    assert claimed.heartbeat_at is not None

    # Success
    svc.record_job_success(
        claimed.id,
        "test-worker-1",
        output_summary={"records_verified": 200},
        duration_ms=45.2,
    )
    db.refresh(claimed)
    assert claimed.status == JobStatus.SUCCEEDED.value
    assert claimed.completed_at is not None
    assert claimed.duration_ms == 45.2
    assert claimed.output_summary["records_verified"] == 200


# ==============================================================================
# Idempotency & Concurrency Tests
# ==============================================================================

def test_job_trigger_idempotency_prevents_duplicate_active_jobs(db):
    """Triggering the same job while active returns existing job without creating duplicates."""
    svc = JobService(db)
    key = f"test-idemp-{uuid.uuid4().hex[:6]}"

    job1, is_new1 = svc.trigger_job(
        job_type=JobType.EVIDENCE_REFRESH.value,
        execution_key=key,
    )
    assert is_new1 is True

    # Immediate second trigger with same execution_key
    job2, is_new2 = svc.trigger_job(
        job_type=JobType.EVIDENCE_REFRESH.value,
        execution_key=key,
    )
    assert is_new2 is False
    assert job2.id == job1.id


def test_concurrency_locking_prevents_double_claiming(db):
    """Once a job is claimed by worker 1, worker 2 cannot claim the same job."""
    svc = JobService(db)
    key = f"test-claim-{uuid.uuid4().hex[:6]}"
    job, _ = svc.trigger_job(
        job_type=JobType.ANALYTICS_REFRESH.value,
        execution_key=key,
    )

    claimed_by_w1 = svc.claim_next_job(worker_id="worker-alpha")
    assert claimed_by_w1 is not None
    assert claimed_by_w1.id == job.id

    # Second worker attempts to claim; should get None (or different job)
    claimed_by_w2 = svc.claim_next_job(worker_id="worker-beta")
    if claimed_by_w2:
        assert claimed_by_w2.id != job.id


def test_stale_job_recovery(db):
    """Jobs left in RUNNING with expired heartbeat are reclaimed for retry."""
    svc = JobService(db)
    key = f"test-stale-{uuid.uuid4().hex[:6]}"
    job, _ = svc.trigger_job(
        job_type=JobType.ANALYTICS_REFRESH.value,
        execution_key=key,
    )

    claimed = svc.claim_next_job(worker_id="crashed-worker")
    # Simulate dead worker by backdating heartbeat
    claimed.heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=120)
    db.commit()

    recovered_count = svc.recover_stale_jobs(timeout_seconds=60.0)
    assert recovered_count >= 1

    db.refresh(claimed)
    assert claimed.status == JobStatus.QUEUED.value
    assert claimed.worker_id is None
    assert "stale_recovery_at" in claimed.retry_metadata


# ==============================================================================
# Retry Strategy Tests
# ==============================================================================

def test_retry_strategy_requeues_until_max_attempts(db):
    """Transient failures are retried up to max_attempts, then marked FAILED."""
    svc = JobService(db)
    key = f"test-retry-{uuid.uuid4().hex[:6]}"
    job, _ = svc.trigger_job(
        job_type=JobType.ANALYTICS_REFRESH.value,
        execution_key=key,
    )
    job.max_attempts = 2
    db.commit()

    # Attempt 1: fail and retry
    claimed = svc.claim_next_job(worker_id="worker-1")
    assert claimed.attempt_count == 1
    svc.record_job_failure(
        claimed.id,
        "worker-1",
        error_code="DB_LOCK_TIMEOUT",
        error_message="Transient lock timeout",
        duration_ms=10.0,
        is_retryable=True,
    )
    db.refresh(claimed)
    assert claimed.status == JobStatus.QUEUED.value

    # Attempt 2: fail and reach terminal failure
    claimed2 = svc.claim_next_job(worker_id="worker-2")
    assert claimed2.id == claimed.id
    assert claimed2.attempt_count == 2
    svc.record_job_failure(
        claimed2.id,
        "worker-2",
        error_code="DB_LOCK_TIMEOUT",
        error_message="Transient lock timeout again",
        duration_ms=12.0,
        is_retryable=True,
    )
    db.refresh(claimed2)
    assert claimed2.status == JobStatus.FAILED.value
    assert claimed2.completed_at is not None


# ==============================================================================
# Domain Job Handlers Tests (Real Persisted Data)
# ==============================================================================

def test_handler_evidence_refresh_idempotent(db):
    """EVIDENCE_REFRESH runs against real database and produces 0 duplicates on rerun."""
    res1 = handle_evidence_refresh(db, payload={})
    assert res1["status"] == "SUCCESS"
    assert "records_discovered" in res1

    # Second run immediately skips already materialized records
    res2 = handle_evidence_refresh(db, payload={})
    assert res2["status"] == "SUCCESS"
    assert res2["evidence_created"] == 0
    assert res2["skipped_existing"] > 0


def test_handler_risk_refresh_evaluates_real_predictions(db):
    """RISK_REFRESH evaluates existing predictions through risk-policy-v1.0.0."""
    res = handle_risk_refresh(db, payload={"machine_id": "TURBOFAN-ENG-001"})
    assert res["status"] == "SUCCESS"
    assert res["policy_version"] == "risk-policy-v1.0.0"
    assert res["machines_evaluated"] >= 1


def test_handler_maintenance_recommendation_refresh_idempotent(db):
    """MAINTENANCE_RECOMMENDATION_REFRESH drafts work orders and respects deduplication."""
    res1 = handle_maintenance_recommendation_refresh(db, payload={})
    assert res1["status"] == "SUCCESS"
    assert res1["policy_version"] == "maintenance-policy-v1.0.0"

    # Second execution must deduplicate 100% of existing items
    res2 = handle_maintenance_recommendation_refresh(db, payload={})
    assert res2["status"] == "SUCCESS"
    assert res2["work_orders_created"] == 0
    assert res2["work_orders_deduplicated"] >= res1["work_orders_deduplicated"]


def test_handler_analytics_refresh_verifies_foundation(db):
    """ANALYTICS_REFRESH verifies 200 turbofans and 33727 telemetry cycles."""
    res = handle_analytics_refresh(db, payload={})
    assert res["status"] == "SUCCESS"
    assert res["total_machines_verified"] == 200
    assert res["total_telemetry_cycles_verified"] == 33727
    assert res["invariance_check"] == "VERIFIED"


# ==============================================================================
# RBAC & API Endpoints Tests
# ==============================================================================

def test_api_viewer_forbidden_from_triggering_jobs(client: TestClient, viewer_token_headers):
    """Viewers are rejected with 403 Forbidden when attempting to trigger background jobs."""
    response = client.post(
        "/api/v1/jobs/EVIDENCE_REFRESH",
        headers=viewer_token_headers,
        json={"payload": {}},
    )
    assert response.status_code == 403


def test_api_operator_allowed_to_trigger_jobs(client: TestClient, operator_token_headers):
    """Operators are authorized to trigger operational refresh jobs (202 Accepted)."""
    response = client.post(
        "/api/v1/jobs/ANALYTICS_REFRESH",
        headers=operator_token_headers,
        json={"payload": {}},
    )
    assert response.status_code in [200, 202]
    data = response.json()
    assert data["job_type"] == "ANALYTICS_REFRESH"
    assert data["status"] in ["QUEUED", "RUNNING", "SUCCEEDED"]


def test_api_unauthorized_job_type_rejected(client: TestClient, operator_token_headers):
    """Attempting to trigger an unknown or arbitrary job type is rejected with 422."""
    response = client.post(
        "/api/v1/jobs/ARBITRARY_CODE_EXECUTION",
        headers=operator_token_headers,
        json={"payload": {}},
    )
    assert response.status_code == 422


def test_api_list_jobs_and_pagination(client: TestClient, viewer_token_headers):
    """Authenticated users can query paginated job history."""
    response = client.get(
        "/api/v1/jobs?skip=0&limit=10",
        headers=viewer_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_api_job_summary_and_freshness(client: TestClient, viewer_token_headers):
    """Summary endpoint returns fleet execution metrics and last refresh timestamps."""
    response = client.get(
        "/api/v1/jobs/summary",
        headers=viewer_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "queued_count" in data
    assert "last_refresh_by_type" in data


def test_api_worker_health_probe(client: TestClient):
    """Worker health probe returns operational status and worker counts."""
    response = client.get("/api/v1/jobs/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database_connected" in data
    assert data["database_connected"] is True


def test_api_job_events_sse_connection(client: TestClient, viewer_token_headers):
    """SSE endpoint establishes an active event stream with connection event."""
    with client.stream(
        "GET",
        "/api/v1/jobs/events?max_events=1",
        headers=viewer_token_headers,
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        # Read the streaming event
        content = response.read().decode("utf-8")
        assert "connected" in content

