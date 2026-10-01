from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy import select

from backend.app.core.risk_policy import (
    AlertSeverity,
    AlertStatus,
    DEFAULT_RISK_POLICY,
    RiskPolicyConfig,
    RiskState,
)
from backend.app.models.alert import Alert
from backend.app.models.audit import AuditLog
from backend.app.models.machine import Machine
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.prediction import Prediction
from backend.app.models.risk import RiskAssessment, RiskTransition
from backend.app.models.user import UserRole
from backend.app.schemas.evidence import EvidenceObject
from backend.app.services.alert_service import AlertService
from backend.app.services.risk_engine import RiskEngine


# --- 1. Risk Engine Unit Tests ---

def test_risk_state_mapping_and_boundaries(db):
    engine = RiskEngine(db)
    machine = db.execute(select(Machine).limit(1)).scalar_one()
    model = db.execute(select(ModelRegistry).where(ModelRegistry.is_active == True)).scalars().first()
    pred_row = db.execute(select(Prediction).where(Prediction.machine_id == machine.id).limit(1)).scalar_one()

    # Case 1: Normal (HI = 0.85)
    pred_normal = Prediction(
        id=uuid.uuid4(),
        machine_id=machine.id,
        model_version_id=model.id,
        feature_engineering_version="1.0.0",
        observation_cycle=10,
        predicted_rul=106.25,
        health_index=0.85,
        operational_state="NORMAL",
    )
    res_normal = engine.evaluate_prediction(pred_normal, machine, persist=False)
    assert res_normal.risk_state == RiskState.NORMAL.value
    assert "HEALTH_INDEX_NORMAL" in res_normal.reason_codes

    # Case 2: Watch (HI = 0.55)
    pred_watch = Prediction(
        id=uuid.uuid4(),
        machine_id=machine.id,
        model_version_id=model.id,
        feature_engineering_version="1.0.0",
        observation_cycle=50,
        predicted_rul=68.75,
        health_index=0.55,
        operational_state="WATCH",
    )
    res_watch = engine.evaluate_prediction(pred_watch, machine, persist=False)
    assert res_watch.risk_state == RiskState.WATCH.value
    assert "HEALTH_INDEX_WATCH" in res_watch.reason_codes

    # Case 3: Elevated (HI = 0.25)
    pred_elevated = Prediction(
        id=uuid.uuid4(),
        machine_id=machine.id,
        model_version_id=model.id,
        feature_engineering_version="1.0.0",
        observation_cycle=100,
        predicted_rul=31.25,
        health_index=0.25,
        operational_state="ELEVATED",
    )
    res_elevated = engine.evaluate_prediction(pred_elevated, machine, persist=False)
    assert res_elevated.risk_state == RiskState.ELEVATED.value
    assert "HEALTH_INDEX_ELEVATED" in res_elevated.reason_codes
    assert "RUL_BELOW_WATCH_THRESHOLD" in res_elevated.reason_codes

    # Case 4: Critical (HI = 0.08)
    pred_crit = Prediction(
        id=uuid.uuid4(),
        machine_id=machine.id,
        model_version_id=model.id,
        feature_engineering_version="1.0.0",
        observation_cycle=150,
        predicted_rul=10.0,
        health_index=0.08,
        operational_state="CRITICAL",
    )
    res_crit = engine.evaluate_prediction(pred_crit, machine, persist=False)
    assert res_crit.risk_state == RiskState.CRITICAL.value
    assert "HEALTH_INDEX_CRITICAL" in res_crit.reason_codes
    assert "RUL_BELOW_ELEVATED_THRESHOLD" in res_crit.reason_codes


def test_boundary_values(db):
    engine = RiskEngine(db)
    machine = db.execute(select(Machine).limit(1)).scalar_one()
    model = db.execute(select(ModelRegistry).where(ModelRegistry.is_active == True)).scalars().first()

    # Exact boundary 0.70 is NORMAL
    p_70 = Prediction(id=uuid.uuid4(), machine_id=machine.id, model_version_id=model.id, observation_cycle=1, predicted_rul=87.5, health_index=0.70)
    assert engine.evaluate_prediction(p_70, machine, persist=False).risk_state == "NORMAL"

    # Just below 0.70 is WATCH
    p_69 = Prediction(id=uuid.uuid4(), machine_id=machine.id, model_version_id=model.id, observation_cycle=1, predicted_rul=87.4, health_index=0.6999)
    assert engine.evaluate_prediction(p_69, machine, persist=False).risk_state == "WATCH"

    # Exact boundary 0.40 is WATCH
    p_40 = Prediction(id=uuid.uuid4(), machine_id=machine.id, model_version_id=model.id, observation_cycle=1, predicted_rul=50.0, health_index=0.40)
    assert engine.evaluate_prediction(p_40, machine, persist=False).risk_state == "WATCH"

    # Just below 0.40 is ELEVATED
    p_39 = Prediction(id=uuid.uuid4(), machine_id=machine.id, model_version_id=model.id, observation_cycle=1, predicted_rul=49.9, health_index=0.3999)
    assert engine.evaluate_prediction(p_39, machine, persist=False).risk_state == "ELEVATED"

    # Exact boundary 0.15 is ELEVATED
    p_15 = Prediction(id=uuid.uuid4(), machine_id=machine.id, model_version_id=model.id, observation_cycle=1, predicted_rul=18.75, health_index=0.15)
    assert engine.evaluate_prediction(p_15, machine, persist=False).risk_state == "ELEVATED"

    # Below 0.15 is CRITICAL
    p_14 = Prediction(id=uuid.uuid4(), machine_id=machine.id, model_version_id=model.id, observation_cycle=1, predicted_rul=18.0, health_index=0.1499)
    assert engine.evaluate_prediction(p_14, machine, persist=False).risk_state == "CRITICAL"


def test_rapid_decline_reason_code(db):
    engine = RiskEngine(db)
    machine = db.execute(select(Machine).limit(1)).scalar_one()
    model = db.execute(select(ModelRegistry).where(ModelRegistry.is_active == True)).scalars().first()

    # Prior prediction at cycle 90 with RUL 80
    prior_pred = Prediction(
        id=uuid.uuid4(),
        machine_id=machine.id,
        model_version_id=model.id,
        feature_engineering_version="1.0.0",
        observation_cycle=90,
        predicted_rul=80.0,
        health_index=0.64,
        operational_state="WATCH",
    )
    db.add(prior_pred)
    db.commit()

    # Current prediction at cycle 95 (cycle delta = 5 <= 10) with RUL 45 (RUL drop = 35 >= 25)
    curr_pred = Prediction(
        id=uuid.uuid4(),
        machine_id=machine.id,
        model_version_id=model.id,
        feature_engineering_version="1.0.0",
        observation_cycle=95,
        predicted_rul=45.0,
        health_index=0.36,
        operational_state="ELEVATED",
    )
    db.add(curr_pred)
    db.commit()

    assessment = engine.evaluate_prediction(curr_pred, machine, persist=False)
    assert "RAPID_RUL_DECLINE" in assessment.reason_codes


def test_explanation_and_policy_version(db):
    engine = RiskEngine(db)
    machine = db.execute(select(Machine).limit(1)).scalar_one()
    model = db.execute(select(ModelRegistry).where(ModelRegistry.is_active == True)).scalars().first()

    pred = Prediction(
        id=uuid.uuid4(),
        machine_id=machine.id,
        model_version_id=model.id,
        feature_engineering_version="1.0.0",
        observation_cycle=100,
        predicted_rul=20.0,
        health_index=0.16,
        operational_state="ELEVATED",
    )
    assessment = engine.evaluate_prediction(pred, machine, persist=False)

    assert assessment.policy_version == "risk-policy-v1.0.0"
    assert "Analytical risk state: ELEVATED" in assessment.explanation
    assert "not a certified safety determination" in assessment.explanation.lower()
    assert "will fail" not in assessment.explanation.lower()


# --- 2. Evidence Layer Tests ---

def test_evidence_object_structure_and_no_fake_confidence(db):
    engine = RiskEngine(db)
    machine = db.execute(select(Machine).limit(1)).scalar_one()

    pred = Prediction(
        machine_id=machine.id,
        model_version_id=uuid.uuid4(),
        feature_engineering_version="1.0.0",
        observation_cycle=50,
        predicted_rul=75.0,
        health_index=0.60,
        operational_state="WATCH",
    )
    assessment = engine.evaluate_prediction(pred, machine, persist=False)

    assert len(assessment.evidence_references) == 2
    rul_ref = next(e for e in assessment.evidence_references if e["evidence_type"] == "RUL_PREDICTION")
    hi_ref = next(e for e in assessment.evidence_references if e["evidence_type"] == "HEALTH_INDEX")

    # Strict rule: confidence MUST be None since regression model is uncalibrated
    assert rul_ref["confidence"] is None
    assert hi_ref["confidence"] is None

    # Source reference links directly to prediction ID
    assert rul_ref["source_reference"] == str(pred.id)
    assert rul_ref["observation_cycle"] == 50
    assert rul_ref["value"] == 75.0
    assert rul_ref["unit"] == "cycles"


# --- 3. Alert System & Deduplication Tests ---

def test_alerts_severity_mapping_and_normal_suppression(db):
    alert_svc = AlertService(db)
    machine = db.execute(select(Machine).limit(1)).scalar_one()
    # Clean any prior alerts on this machine
    for a in list(db.execute(select(Alert).where(Alert.machine_id == machine.id)).scalars().all()):
        db.delete(a)
    db.commit()
    pred = db.execute(select(Prediction).where(Prediction.machine_id == machine.id).limit(1)).scalar_one()

    # 1. NORMAL state generates NO alert
    norm_assess = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=machine.id,
        prediction_id=pred.id,
        risk_state="NORMAL",
        health_index=0.85,
        predicted_rul=106.0,
        policy_version="risk-policy-v1.0.0",
        explanation="Normal",
    )
    db.add(norm_assess)
    db.commit()
    assert alert_svc.process_risk_assessment(norm_assess, machine) is None

    # 2. WATCH generates INFO alert
    watch_assess = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=machine.id,
        prediction_id=pred.id,
        risk_state="WATCH",
        health_index=0.55,
        predicted_rul=68.0,
        policy_version="risk-policy-v1.0.0",
        explanation="Watch",
    )
    db.add(watch_assess)
    db.commit()
    watch_alert = alert_svc.process_risk_assessment(watch_assess, machine)
    assert watch_alert is not None
    assert watch_alert.severity == AlertSeverity.INFO.value
    assert watch_alert.status == AlertStatus.OPEN.value

    # 3. ELEVATED generates WARNING alert
    elev_assess = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=machine.id,
        prediction_id=pred.id,
        risk_state="ELEVATED",
        health_index=0.25,
        predicted_rul=31.0,
        policy_version="risk-policy-v1.0.0",
        explanation="Elevated",
    )
    db.add(elev_assess)
    db.commit()
    elev_alert = alert_svc.process_risk_assessment(elev_assess, machine)
    assert elev_alert is not None
    assert elev_alert.severity == AlertSeverity.WARNING.value

    # 4. CRITICAL generates CRITICAL alert
    crit_assess = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=machine.id,
        prediction_id=pred.id,
        risk_state="CRITICAL",
        health_index=0.05,
        predicted_rul=6.0,
        policy_version="risk-policy-v1.0.0",
        explanation="Critical",
    )
    db.add(crit_assess)
    db.commit()
    crit_alert = alert_svc.process_risk_assessment(crit_assess, machine)
    assert crit_alert is not None
    assert crit_alert.severity == AlertSeverity.CRITICAL.value


def test_alert_deduplication(db):
    alert_svc = AlertService(db)
    # Pick a fresh machine with no active alerts
    machine = db.execute(select(Machine).order_by(Machine.machine_id.desc()).limit(1)).scalar_one()
    # Delete any existing alerts for this machine in test transaction
    alerts_to_clean = list(db.execute(select(Alert).where(Alert.machine_id == machine.id)).scalars().all())
    for a in alerts_to_clean:
        db.delete(a)
    db.commit()

    pred = db.execute(select(Prediction).where(Prediction.machine_id == machine.id).limit(1)).scalar_one()

    crit_assess_1 = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=machine.id,
        prediction_id=pred.id,
        risk_state="CRITICAL",
        health_index=0.08,
        predicted_rul=10.0,
        policy_version="risk-policy-v1.0.0",
        explanation="Crit 1",
    )
    db.add(crit_assess_1)
    db.commit()
    alert_1 = alert_svc.process_risk_assessment(crit_assess_1, machine)
    assert alert_1 is not None

    # Immediate second critical assessment for same machine: must be deduplicated
    crit_assess_2 = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=machine.id,
        prediction_id=pred.id,
        risk_state="CRITICAL",
        health_index=0.07,
        predicted_rul=9.0,
        policy_version="risk-policy-v1.0.0",
        explanation="Crit 2",
    )
    db.add(crit_assess_2)
    db.commit()
    alert_2 = alert_svc.process_risk_assessment(crit_assess_2, machine)
    assert alert_2 is None  # Suppressed by deduplication


def test_alert_lifecycle_and_auditability(db, create_test_user):
    alert_svc = AlertService(db)
    machine = db.execute(select(Machine).limit(1)).scalar_one()
    operator = create_test_user(username="op_user", role=UserRole.OPERATOR)
    pred = db.execute(select(Prediction).where(Prediction.machine_id == machine.id).limit(1)).scalar_one()

    # Clear prior active alerts for this machine in test
    alerts_to_clean = list(db.execute(select(Alert).where(Alert.machine_id == machine.id)).scalars().all())
    for a in alerts_to_clean:
        db.delete(a)
    db.commit()

    assess = RiskAssessment(
        id=uuid.uuid4(),
        machine_id=machine.id,
        prediction_id=pred.id,
        risk_state="ELEVATED",
        health_index=0.25,
        predicted_rul=31.0,
        policy_version="risk-policy-v1.0.0",
        explanation="Elevated",
    )
    db.add(assess)
    db.commit()
    alert = alert_svc.process_risk_assessment(assess, machine)
    assert alert is not None
    assert alert.status == AlertStatus.OPEN.value

    # 1. Acknowledge Alert
    ack_alert = alert_svc.acknowledge_alert(alert.id, actor=operator, comment="Under inspection")
    assert ack_alert.status == AlertStatus.ACKNOWLEDGED.value
    assert ack_alert.acknowledged_at is not None
    assert ack_alert.acknowledged_by_id == operator.id

    # Verify audit log
    audit_ack = db.execute(
        select(AuditLog).where(AuditLog.target_id == str(alert.id), AuditLog.action == "ALERT_ACKNOWLEDGED")
    ).scalar_one_or_none()
    assert audit_ack is not None
    assert audit_ack.actor_id == operator.id

    # 2. Resolve Alert
    res_alert = alert_svc.resolve_alert(alert.id, actor=operator, comment="Filter replaced")
    assert res_alert.status == AlertStatus.RESOLVED.value
    assert res_alert.resolved_at is not None
    assert res_alert.resolved_by_id == operator.id

    # Verify audit log
    audit_res = db.execute(
        select(AuditLog).where(AuditLog.target_id == str(alert.id), AuditLog.action == "ALERT_RESOLVED")
    ).scalar_one_or_none()
    assert audit_res is not None
    assert audit_res.actor_id == operator.id


# --- 4. API & RBAC Tests ---

def test_api_risk_latest_and_history(client, operator_token_headers):
    # GET latest risk
    latest_res = client.get("/api/v1/machines/TURBOFAN-ENG-001/risk/latest", headers=operator_token_headers)
    assert latest_res.status_code == 200
    data = latest_res.json()
    assert data is not None
    assert "risk_state" in data
    assert "evidence_references" in data

    # GET risk history
    hist_res = client.get("/api/v1/machines/TURBOFAN-ENG-001/risk/history?page=1&page_size=10", headers=operator_token_headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["total"] >= 1
    assert len(hist_data["items"]) >= 1


def test_api_risk_on_demand_evaluate(client, operator_token_headers):
    eval_res = client.post(
        "/api/v1/machines/TURBOFAN-ENG-002/risk/evaluate",
        json={"observation_cycle": 150},
        headers=operator_token_headers,
    )
    assert eval_res.status_code == 201
    eval_data = eval_res.json()
    assert eval_data["machine_name"] == "TURBOFAN-ENG-002"
    assert eval_data["risk_state"] in [s.value for s in RiskState]
    assert len(eval_data["evidence_references"]) == 2


def test_api_alerts_list_and_summary(client, operator_token_headers):
    # GET summary
    summary_res = client.get("/api/v1/alerts/summary", headers=operator_token_headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_alerts"] >= 1
    assert "by_severity" in summary

    # GET list
    list_res = client.get("/api/v1/alerts?page=1&page_size=20", headers=operator_token_headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_api_rbac_viewer_cannot_mutate_alerts(client, viewer_token_headers, operator_token_headers):
    # Get an open alert
    alerts_res = client.get("/api/v1/alerts?status=OPEN&page_size=1", headers=viewer_token_headers)
    alerts = alerts_res.json()["items"]
    if not alerts:
        pytest.skip("No open alert found to test RBAC")

    target_alert_id = alerts[0]["id"]

    # VIEWER tries to acknowledge: MUST fail with 403 Forbidden
    ack_res = client.post(
        f"/api/v1/alerts/{target_alert_id}/acknowledge",
        json={"comment": "Unauthorized attempt"},
        headers=viewer_token_headers,
    )
    assert ack_res.status_code == 403

    # OPERATOR tries to acknowledge: MUST succeed with 200 OK
    op_ack_res = client.post(
        f"/api/v1/alerts/{target_alert_id}/acknowledge",
        json={"comment": "Operator authorized acknowledgment"},
        headers=operator_token_headers,
    )
    assert op_ack_res.status_code == 200
    assert op_ack_res.json()["status"] == "ACKNOWLEDGED"

    # OPERATOR resolves: MUST succeed with 200 OK
    op_res_res = client.post(
        f"/api/v1/alerts/{target_alert_id}/resolve",
        json={"comment": "Operator authorized resolution"},
        headers=operator_token_headers,
    )
    assert op_res_res.status_code == 200
    assert op_res_res.json()["status"] == "RESOLVED"
