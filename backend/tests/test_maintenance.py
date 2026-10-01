from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.models.audit import AuditLog
from backend.app.models.evidence import EvidenceRecord, EvidenceRelationship
from backend.app.models.inspection import InspectionResult, InspectionRun
from backend.app.models.machine import Machine, MachineStatus, MachineType, SplitCategory
from backend.app.models.maintenance import (
    MaintenanceEvent,
    MaintenancePriority,
    MaintenanceSourceDomain,
    MaintenanceSourceType,
    MaintenanceStatus,
    MaintenanceWorkOrder,
)
from backend.app.models.risk import RiskAssessment
from backend.app.models.user import UserRole
from backend.app.services.maintenance_service import (
    MAINTENANCE_POLICY_VERSION,
    MaintenanceService,
)


@pytest.fixture
def sample_machine(db):
    uid = uuid.uuid4().hex[:6]
    m = Machine(
        machine_id=f"TEST_ENGINE_{uid}",
        name=f"Turbofan Test {uid}",
        machine_type=MachineType.TURBOFAN_ENGINE,
        source_dataset="c_mapss_fd001",
        source_entity_id=f"unit_{uid}",
        status=MachineStatus.OPERATIONAL,
        split_category=SplitCategory.EVAL_TEST,
        total_cycles=150,
        max_cycle=150,
        metadata_json={},
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


from backend.app.models.model_registry import ModelRegistry
from backend.app.models.prediction import Prediction


@pytest.fixture
def sample_prediction(db, sample_machine):
    model = db.query(ModelRegistry).first()
    if not model:
        model = ModelRegistry(
            id=uuid.uuid4(),
            model_id=f"test_model_{uuid.uuid4().hex[:6]}",
            model_name="RandomForestRegressor",
            algorithm="random_forest",
            task="RUL_REGRESSION",
            dataset_identifier="c_mapss_fd001",
            artifact_path="/tmp/test_artifact.joblib",
            is_active=True,
        )
        db.add(model)
        db.flush()

    pred = Prediction(
        id=uuid.uuid4(),
        machine_id=sample_machine.id,
        model_version_id=model.id,
        feature_engineering_version="1.0.0",
        observation_cycle=150,
        predicted_rul=12.5,
        health_index=0.15,
        operational_state="CRITICAL",
        metadata_json={},
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


@pytest.fixture
def sample_risk_critical(db, sample_machine, sample_prediction):
    r = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=sample_machine.id,
        prediction_id=sample_prediction.id,
        risk_state="CRITICAL",
        predicted_rul=12.5,
        health_index=0.15,
        reason_codes=["LOW_RUL", "HEALTH_INDEX_CRITICAL"],
        explanation="C-MAPSS asset estimated RUL is 12.5 cycles.",
        evidence_references=[{"rul": 12.5}],
        policy_version="risk-policy-v1.0.0",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@pytest.fixture
def sample_risk_elevated(db, sample_machine, sample_prediction):
    r = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=sample_machine.id,
        prediction_id=sample_prediction.id,
        risk_state="ELEVATED",
        predicted_rul=35.0,
        health_index=0.45,
        reason_codes=["ELEVATED_DEGRADATION"],
        explanation="C-MAPSS asset estimated RUL is 35.0 cycles.",
        evidence_references=[{"rul": 35.0}],
        policy_version="risk-policy-v1.0.0",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@pytest.fixture
def sample_risk_normal(db, sample_machine, sample_prediction):
    r = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=sample_machine.id,
        prediction_id=sample_prediction.id,
        risk_state="NORMAL",
        predicted_rul=110.0,
        health_index=0.92,
        reason_codes=[],
        explanation="C-MAPSS asset estimated RUL is 110.0 cycles.",
        evidence_references=[],
        policy_version="risk-policy-v1.0.0",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@pytest.fixture
def sample_inspection_defect(db):
    run = InspectionRun(
        id=uuid.uuid4(),
        dataset_identifier="mvtec_ad",
        category="metal_nut",
        model_version="v1.0.0",
        feature_config_version="v1.0.0",
        policy_version="inspection-policy-v1.0.0",
        threshold=2.50,
        total_images=1,
        passed_count=0,
        defect_count=1,
        status="COMPLETED",
        evaluation_summary={},
    )
    db.add(run)
    db.flush()

    res = InspectionResult(
        id=uuid.uuid4(),
        run_id=run.id,
        split="test",
        defect_class="scratch",
        source_image_path="/path/to/test_scratch.png",
        source_image_filename="test_scratch.png",
        image_level_score=4.82,
        decision="DEFECT",
        ground_truth_label="DEFECT",
        heatmap_path="/path/to/test_heatmap.png",
        overlay_path="/path/to/test_overlay.png",
        ground_truth_mask_path=None,
        inference_metadata={},
    )
    db.add(res)
    db.commit()
    db.refresh(res)
    return res


@pytest.fixture
def sample_inspection_pass(db):
    run = InspectionRun(
        id=uuid.uuid4(),
        dataset_identifier="mvtec_ad",
        category="metal_nut",
        model_version="v1.0.0",
        feature_config_version="v1.0.0",
        policy_version="inspection-policy-v1.0.0",
        threshold=2.50,
        total_images=1,
        passed_count=1,
        defect_count=0,
        status="COMPLETED",
        evaluation_summary={},
    )
    db.add(run)
    db.flush()

    res = InspectionResult(
        id=uuid.uuid4(),
        run_id=run.id,
        split="test",
        defect_class="good",
        source_image_path="/path/to/test_good.png",
        source_image_filename="test_good.png",
        image_level_score=1.12,
        decision="PASS",
        ground_truth_label="PASS",
        heatmap_path=None,
        overlay_path=None,
        ground_truth_mask_path=None,
        inference_metadata={},
    )
    db.add(res)
    db.commit()
    db.refresh(res)
    return res


def _get_err(resp) -> str:
    body = resp.json()
    if isinstance(body, dict):
        if "error" in body and isinstance(body["error"], dict):
            return body["error"].get("message", "")
        return body.get("detail", "")
    return ""


# =========================================================================
# 1. Recommendation Generation and Policy Tests
# =========================================================================

def test_recommendation_from_critical_risk(client: TestClient, operator_token_headers, sample_risk_critical):
    """Verifies that a CRITICAL risk assessment drafts a CRITICAL priority work order with correct actions."""
    resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_domain"] == "MACHINE_HEALTH"
    assert data["source_type"] == "RISK_ASSESSMENT"
    assert data["source_reference"] == str(sample_risk_critical.id)
    assert data["priority"] == "CRITICAL"
    assert data["status"] == "OPEN"
    assert data["risk_state_at_creation"] == "CRITICAL"
    assert data["predicted_rul_at_creation"] == 12.5
    assert "Prioritize human review" in data["recommended_action"]


def test_recommendation_from_elevated_risk(client: TestClient, operator_token_headers, sample_risk_elevated):
    """Verifies that an ELEVATED risk assessment drafts a HIGH priority work order."""
    resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_elevated.id}",
        headers=operator_token_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["priority"] == "HIGH"
    assert "Review recent machine-health evidence and schedule inspection" in data["recommended_action"]


def test_reject_recommendation_for_normal_risk(client: TestClient, operator_token_headers, sample_risk_normal):
    """Verifies policy rejects maintenance work order creation for NORMAL assets."""
    resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_normal.id}",
        headers=operator_token_headers,
    )
    assert resp.status_code == 400
    assert "NORMAL" in _get_err(resp)


def test_recommendation_from_defect_inspection(client: TestClient, operator_token_headers, sample_inspection_defect):
    """Verifies visual inspection DEFECT drafts a VISUAL_INSPECTION work order."""
    resp = client.post(
        f"/api/v1/maintenance/recommendations/from-inspection/{sample_inspection_defect.id}",
        headers=operator_token_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_domain"] == "VISUAL_INSPECTION"
    assert data["source_type"] == "INSPECTION_RESULT"
    assert data["priority"] == "HIGH"
    assert data["status"] == "OPEN"
    assert data["anomaly_score_at_creation"] == 4.82
    assert "Review the inspection image" in data["recommended_action"]


def test_reject_recommendation_for_pass_inspection(client: TestClient, operator_token_headers, sample_inspection_pass):
    """Verifies policy rejects maintenance recommendations for PASS inspection results."""
    resp = client.post(
        f"/api/v1/maintenance/recommendations/from-inspection/{sample_inspection_pass.id}",
        headers=operator_token_headers,
    )
    assert resp.status_code == 400
    assert "PASS" in _get_err(resp)


# =========================================================================
# 2. Deduplication Tests
# =========================================================================

def test_deduplication_returns_existing_work_order(client: TestClient, operator_token_headers, sample_risk_critical):
    """Calling recommendation creation twice for the same source must return the existing work order without creating a duplicate."""
    resp1 = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )
    assert resp1.status_code == 201
    wo1 = resp1.json()

    # Second call
    resp2 = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )
    assert resp2.status_code == 201
    wo2 = resp2.json()

    assert wo1["id"] == wo2["id"]
    assert wo1["deduplication_key"] == wo2["deduplication_key"]

    # Verify total count in list endpoint is exactly 1 for this source
    list_resp = client.get(
        f"/api/v1/maintenance/work-orders?machine_id={wo1['machine_id']}",
        headers=operator_token_headers,
    )
    assert list_resp.status_code == 200
    items = [item for item in list_resp.json() if item["source_reference"] == str(sample_risk_critical.id)]
    assert len(items) == 1


# =========================================================================
# 3. Lifecycle Transitions Tests
# =========================================================================

def test_full_successful_lifecycle(client: TestClient, operator_token_headers, sample_risk_critical):
    """Tests the full controlled lifecycle: OPEN -> ACKNOWLEDGED -> IN_PROGRESS -> COMPLETED."""
    # 1. Create OPEN
    create_resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )
    wo_id = create_resp.json()["id"]

    # 2. Acknowledge
    ack_resp = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/acknowledge",
        headers=operator_token_headers,
        json={"notes": "Assigned to shift team."},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"
    assert ack_resp.json()["acknowledged_at"] is not None

    # 3. Start
    start_resp = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/start",
        headers=operator_token_headers,
        json={"notes": "Beginning sensor line inspection."},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "IN_PROGRESS"
    assert start_resp.json()["started_at"] is not None

    # 4. Complete
    complete_resp = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/complete",
        headers=operator_token_headers,
        json={"resolution_notes": "Turbofan combustor casing verified and vibration transducer recalibrated."},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "COMPLETED"
    assert complete_resp.json()["completed_at"] is not None
    assert "Turbofan combustor" in complete_resp.json()["resolution_notes"]

    # 5. Verify Detail & Immutable Events
    detail_resp = client.get(
        f"/api/v1/maintenance/work-orders/{wo_id}",
        headers=operator_token_headers,
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "COMPLETED"
    event_types = [e["event_type"] for e in detail["events"]]
    assert event_types == ["CREATED", "ACKNOWLEDGED", "STARTED", "COMPLETED"]


def test_cancellation_lifecycle(client: TestClient, operator_token_headers, sample_risk_elevated):
    """Tests cancellation transition from OPEN -> CANCELLED with recorded reason."""
    create_resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_elevated.id}",
        headers=operator_token_headers,
    )
    wo_id = create_resp.json()["id"]

    cancel_resp = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/cancel",
        headers=operator_token_headers,
        json={"reason": "False alarm: sensor baseline recalibrated prior to shift."},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
    assert cancel_resp.json()["cancelled_at"] is not None
    assert "False alarm" in cancel_resp.json()["resolution_notes"]


def test_invalid_lifecycle_transitions(client: TestClient, operator_token_headers, sample_risk_critical):
    """Verifies that illegal status transitions are rejected with 400 Bad Request."""
    create_resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )
    wo_id = create_resp.json()["id"]

    # Cannot complete directly from OPEN
    bad_comp = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/complete",
        headers=operator_token_headers,
        json={"resolution_notes": "Trying to skip in-progress step."},
    )
    assert bad_comp.status_code == 400
    assert "IN_PROGRESS" in _get_err(bad_comp)

    # Cannot start directly from OPEN without acknowledging
    bad_start = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/start",
        headers=operator_token_headers,
    )
    assert bad_start.status_code == 400
    assert "ACKNOWLEDGED" in _get_err(bad_start)


def test_complete_requires_resolution_notes(client: TestClient, operator_token_headers, sample_risk_critical):
    """Completion must enforce non-empty human resolution notes."""
    create_resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )
    wo_id = create_resp.json()["id"]

    client.post(f"/api/v1/maintenance/work-orders/{wo_id}/acknowledge", headers=operator_token_headers)
    client.post(f"/api/v1/maintenance/work-orders/{wo_id}/start", headers=operator_token_headers)

    # Empty resolution notes
    bad_req = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/complete",
        headers=operator_token_headers,
        json={"resolution_notes": "  "},
    )
    assert bad_req.status_code in (400, 422)


# =========================================================================
# 4. RBAC Tests
# =========================================================================

def test_viewer_cannot_mutate_work_orders(client: TestClient, viewer_token_headers, operator_token_headers, sample_risk_critical):
    """Verifies that VIEWER role is strictly forbidden from creating or modifying work orders."""
    # VIEWER cannot create recommendation
    resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 403

    # Create with OPERATOR
    op_create = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )
    wo_id = op_create.json()["id"]

    # VIEWER can READ
    get_resp = client.get(
        f"/api/v1/maintenance/work-orders/{wo_id}",
        headers=viewer_token_headers,
    )
    assert get_resp.status_code == 200

    # VIEWER cannot ACKNOWLEDGE
    ack_resp = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/acknowledge",
        headers=viewer_token_headers,
    )
    assert ack_resp.status_code == 403

    # VIEWER cannot CANCEL
    cancel_resp = client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/cancel",
        headers=viewer_token_headers,
        json={"reason": "Viewer attempting cancel"},
    )
    assert cancel_resp.status_code == 403


# =========================================================================
# 5. Audit Trail & Evidence Lineage Tests
# =========================================================================

def test_audit_log_and_evidence_integration(client: TestClient, operator_token_headers, sample_risk_critical, db):
    """Verifies that creating and completing a work order produces AuditLog entries and EvidenceRecord outcomes."""
    # 1. Create work order
    create_resp = client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )
    wo_id = create_resp.json()["id"]

    # Verify AuditLog created
    audit = db.query(AuditLog).filter(
        AuditLog.target_id == str(wo_id),
        AuditLog.action == "MAINTENANCE_WORK_ORDER_CREATED",
    ).first()
    assert audit is not None

    # Complete lifecycle
    client.post(f"/api/v1/maintenance/work-orders/{wo_id}/acknowledge", headers=operator_token_headers)
    client.post(f"/api/v1/maintenance/work-orders/{wo_id}/start", headers=operator_token_headers)
    client.post(
        f"/api/v1/maintenance/work-orders/{wo_id}/complete",
        headers=operator_token_headers,
        json={"resolution_notes": "Visual crack inspection completed. Thermal barrier coating intact."},
    )

    # Verify Outcome Evidence Record created
    outcome_evidence = db.query(EvidenceRecord).filter(
        EvidenceRecord.entity_id == str(wo_id),
        EvidenceRecord.evidence_type == "MAINTENANCE_OUTCOME",
    ).first()
    assert outcome_evidence is not None
    assert outcome_evidence.quality_state == "VERIFIED"
    assert outcome_evidence.domain == "MACHINE_HEALTH"
    assert "Thermal barrier coating intact" in outcome_evidence.explanation


# =========================================================================
# 6. Summary and Listing Tests
# =========================================================================

def test_maintenance_summary_endpoint(client: TestClient, operator_token_headers, sample_risk_critical):
    """Verifies the /api/v1/maintenance/summary KPI aggregation endpoint."""
    client.post(
        f"/api/v1/maintenance/recommendations/from-risk/{sample_risk_critical.id}",
        headers=operator_token_headers,
    )

    resp = client.get("/api/v1/maintenance/summary", headers=operator_token_headers)
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["total_work_orders"] >= 1
    assert "critical_priority_count" in summary
    assert "open_count" in summary
    assert isinstance(summary["recent_activity"], list)
