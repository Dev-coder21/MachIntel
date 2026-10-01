import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.model_registry import (
    ModelRegistry,
    ModelEvaluation,
    ModelPromotion,
    ModelDomain,
    ModelLifecycleStatus,
    EvaluationGateResult,
)
from backend.app.services.model_lifecycle_service import (
    ModelLifecycleService,
    safe_resolve_artifact_path,
)
from backend.app.worker.handlers import handle_model_integrity_check
from backend.app.models.job import BackgroundJob, JobType, JobStatus


def test_seed_verified_models(db: Session):
    """Verify that verified historical models are seeded with correct metadata and checksums."""
    seeded = ModelLifecycleService.seed_verified_models(db)
    assert len(seeded) >= 2

    rf = db.query(ModelRegistry).filter(ModelRegistry.model_id == "rul-randomforest-v1.0.0").first()
    assert rf is not None
    assert rf.domain == ModelDomain.MACHINE_HEALTH
    assert rf.status == ModelLifecycleStatus.PROMOTED
    assert rf.is_active is True
    assert rf.artifact_sha256 == "186cda72751d0cfbe3408968b6682e65b993d7fd972646bce0c914e999571b1b"
    assert rf.artifact_size_bytes == 17435969
    assert rf.dataset_identifier == "NASA-C-MAPSS-FD001"

    ridge = db.query(ModelRegistry).filter(ModelRegistry.model_id == "rul-ridge-v1.0.0").first()
    assert ridge is not None
    assert ridge.domain == ModelDomain.MACHINE_HEALTH
    assert ridge.status == ModelLifecycleStatus.EVALUATED
    assert ridge.is_active is False
    assert ridge.artifact_sha256 == "6eacb3d910542fe2e3349cd0451a22428aa58d6af2240d4a82fbf15ed96946bf"

    # Evaluations exist and are linked
    evals = db.query(ModelEvaluation).filter(ModelEvaluation.model_version_id == rf.id).all()
    assert len(evals) >= 1
    assert evals[0].gate_result == EvaluationGateResult.PASSED
    assert evals[0].metrics["val_rmse"] == 19.5411


def test_list_and_filter_models(client: TestClient, db: Session, viewer_token_headers: dict):
    """Test model listing and domain/status filtering."""
    ModelLifecycleService.seed_verified_models(db)

    # All models
    res = client.get("/api/v1/models", headers=viewer_token_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2
    assert "active_machine_health_model_id" in data

    # Filter domain
    res_mh = client.get("/api/v1/models?domain=MACHINE_HEALTH", headers=viewer_token_headers)
    assert res_mh.status_code == 200
    for item in res_mh.json()["items"]:
        assert item["domain"] == "MACHINE_HEALTH"

    # Filter status
    res_promoted = client.get("/api/v1/models?status=PROMOTED", headers=viewer_token_headers)
    assert res_promoted.status_code == 200
    for item in res_promoted.json()["items"]:
        assert item["status"] == "PROMOTED"


def test_get_model_details(client: TestClient, db: Session, viewer_token_headers: dict):
    """Test retrieving detail of a specific model by model_id."""
    ModelLifecycleService.seed_verified_models(db)

    res = client.get("/api/v1/models/rul-randomforest-v1.0.0", headers=viewer_token_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["model_id"] == "rul-randomforest-v1.0.0"
    assert data["domain"] == "MACHINE_HEALTH"
    assert data["artifact_sha256"] is not None
    assert "NASA-C-MAPSS" in data["dataset_identifier"]


def test_artifact_integrity_verification(client: TestClient, db: Session, viewer_token_headers: dict):
    """Test cryptographic SHA-256 integrity verification."""
    ModelLifecycleService.seed_verified_models(db)

    res = client.get("/api/v1/models/rul-randomforest-v1.0.0/integrity", headers=viewer_token_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["expected_sha256"] == data["computed_sha256"]
    assert data["file_size_bytes"] == 17435969


def test_artifact_integrity_mismatch_detection(db: Session):
    """Test that integrity verification flags mismatch if stored digest does not match actual file."""
    ModelLifecycleService.seed_verified_models(db)
    rf = db.query(ModelRegistry).filter(ModelRegistry.model_id == "rul-randomforest-v1.0.0").first()

    # Corrupt the expected digest in the database
    rf.artifact_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
    db.commit()

    report = ModelLifecycleService.verify_artifact_integrity(rf)
    assert report["is_valid"] is False
    assert "mismatch" in report["details"].get("error", "").lower()


def test_promotion_gates_evaluation(client: TestClient, db: Session, viewer_token_headers: dict):
    """Test deterministic evaluation gates for promoted model."""
    ModelLifecycleService.seed_verified_models(db)

    res = client.get("/api/v1/models/rul-randomforest-v1.0.0/gates", headers=viewer_token_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["can_promote"] is True
    assert "GATE_1_ARTIFACT_EXISTS" in data["passed_gates"]
    assert "GATE_2_CHECKSUM_VALID" in data["passed_gates"]
    assert "GATE_7_EVALUATION_PASSED" in data["passed_gates"]
    assert len(data["failed_gates"]) == 0


def test_promotion_lifecycle_and_audit(client: TestClient, db: Session, admin_token_headers: dict):
    """Test promoting candidate model, superseding previous active model, and auditing transition."""
    ModelLifecycleService.seed_verified_models(db)

    # First verify ridge is EVALUATED
    ridge = db.query(ModelRegistry).filter(ModelRegistry.model_id == "rul-ridge-v1.0.0").first()
    assert ridge.status == ModelLifecycleStatus.EVALUATED
    assert ridge.is_active is False

    # Promote ridge
    res = client.post(
        f"/api/v1/models/{ridge.model_id}/promote",
        headers=admin_token_headers,
        json={"reason": "Explicit operator-approved benchmark verification"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PROMOTED"
    assert data["is_active"] is True

    # Verify previous active model (RF) was retired
    rf = db.query(ModelRegistry).filter(ModelRegistry.model_id == "rul-randomforest-v1.0.0").first()
    assert rf.status == ModelLifecycleStatus.RETIRED
    assert rf.is_active is False

    # Verify audit logs in model_promotions
    promos = client.get(f"/api/v1/models/{ridge.model_id}/promotions", headers=admin_token_headers).json()
    assert len(promos) >= 1
    assert promos[0]["to_status"] == "PROMOTED"
    assert "Explicit operator-approved" in promos[0]["reason"]


def test_retire_model(client: TestClient, db: Session, admin_token_headers: dict):
    """Test retiring an active model."""
    ModelLifecycleService.seed_verified_models(db)

    res = client.post(
        "/api/v1/models/rul-randomforest-v1.0.0/retire",
        headers=admin_token_headers,
        json={"reason": "Decommissioning legacy release"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RETIRED"
    assert data["is_active"] is False


def test_rbac_security(client: TestClient, db: Session, viewer_token_headers: dict, operator_token_headers: dict):
    """Verify that VIEWER and OPERATOR cannot register, promote, or retire models."""
    ModelLifecycleService.seed_verified_models(db)

    # VIEWER cannot promote
    res_v = client.post(
        "/api/v1/models/rul-ridge-v1.0.0/promote",
        headers=viewer_token_headers,
        json={"reason": "Unauthorized"},
    )
    assert res_v.status_code == 403

    # OPERATOR cannot promote
    res_o = client.post(
        "/api/v1/models/rul-ridge-v1.0.0/promote",
        headers=operator_token_headers,
        json={"reason": "Unauthorized"},
    )
    assert res_o.status_code == 403

    # OPERATOR cannot retire
    res_retire = client.post(
        "/api/v1/models/rul-randomforest-v1.0.0/retire",
        headers=operator_token_headers,
        json={"reason": "Unauthorized"},
    )
    assert res_retire.status_code == 403


def test_path_traversal_protection(client: TestClient, db: Session, admin_token_headers: dict):
    """Verify that safe_resolve_artifact_path prevents path traversal and path injection."""
    from fastapi import HTTPException
    # Attempt to resolve an outside path
    with pytest.raises(HTTPException) as exc_info:
        safe_resolve_artifact_path("../../etc/passwd")
    assert exc_info.value.status_code == 400
    assert "Security violation" in exc_info.value.detail

    with pytest.raises(HTTPException) as exc_info2:
        safe_resolve_artifact_path("/etc/shadow")
    assert exc_info2.value.status_code == 400


def test_model_registration_version_uniqueness(client: TestClient, db: Session, admin_token_headers: dict):
    """Verify model registration and duplicate model_id rejection."""
    ModelLifecycleService.seed_verified_models(db)

    payload = {
        "model_id": "rul-randomforest-v1.0.0",  # Already exists
        "model_name": "Duplicate Model",
        "domain": "MACHINE_HEALTH",
        "model_family": "RUL_REGRESSION",
        "algorithm": "RandomForestRegressor",
        "task": "RUL_REGRESSION",
        "version": "1.0.0",
        "status": "REGISTERED",
        "framework": "scikit-learn",
        "dataset_identifier": "NASA-C-MAPSS-FD001",
        "artifact_path": "storage/models/rul/rul-randomforest-v1.0.0",
        "artifact_sha256": "186cda72751d0cfbe3408968b6682e65b993d7fd972646bce0c914e999571b1b",
    }

    res = client.post("/api/v1/models/register", headers=admin_token_headers, json=payload)
    assert res.status_code == 400
    err_body = res.json().get("error", {})
    assert "already registered" in err_body.get("message", "")


def test_active_model_resolution_and_failsafe(db: Session):
    """Verify active model resolution by domain and fail-safe on checksum corruption."""
    from fastapi import HTTPException
    ModelLifecycleService.seed_verified_models(db)

    # Normal resolution
    active = ModelLifecycleService.get_active_model(db, "MACHINE_HEALTH")
    assert active.model_id == "rul-randomforest-v1.0.0"
    assert active.is_active is True

    # Deliberately corrupt checksum
    active.artifact_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        ModelLifecycleService.get_active_model(db, "MACHINE_HEALTH")
    assert exc_info.value.status_code == 500
    assert "failed SHA-256 integrity verification" in exc_info.value.detail


def test_model_integrity_job_handler(db: Session):
    """Verify that background worker executes MODEL_INTEGRITY_CHECK job deterministically."""
    ModelLifecycleService.seed_verified_models(db)

    job = BackgroundJob(
        job_type=JobType.MODEL_INTEGRITY_CHECK.value,
        payload={"model_id": "rul-randomforest-v1.0.0"},
        status=JobStatus.QUEUED.value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    result = handle_model_integrity_check(db, job.payload)
    assert result["status"] == "SUCCESS"
    assert result["models_checked"] == 1
    assert result["models_passed"] == 1
    assert result["models_failed"] == 0
