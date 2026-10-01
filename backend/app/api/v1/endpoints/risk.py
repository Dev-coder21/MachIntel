from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.machine import Machine
from backend.app.models.risk import RiskAssessment
from backend.app.models.user import User, UserRole
from backend.app.schemas.risk import (
    RiskAssessmentListResponse,
    RiskAssessmentResponse,
    RiskEvaluationRequest,
)
from backend.app.services.alert_service import AlertService
from backend.app.services.prediction_service import PredictionService
from backend.app.services.risk_engine import RiskEngine

router = APIRouter(tags=["Risk Engine & Intelligence"])


def _resolve_machine(db: Session, machine_id_str: str) -> Machine:
    try:
        val_uuid = uuid.UUID(machine_id_str)
        machine = db.execute(
            select(Machine).where(
                (Machine.machine_id == machine_id_str) | (Machine.id == val_uuid)
            )
        ).scalar_one_or_none()
    except (ValueError, AttributeError):
        machine = db.execute(
            select(Machine).where(Machine.machine_id == machine_id_str)
        ).scalar_one_or_none()

    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id_str}' not found.",
        )
    return machine


@router.get(
    "/machines/{machine_id}/risk/latest",
    response_model=Optional[RiskAssessmentResponse],
    summary="Get latest analytical risk assessment for an asset",
)
def get_latest_risk(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Optional[RiskAssessmentResponse]:
    """Retrieves the most recent deterministic risk assessment and evidence references."""
    machine = _resolve_machine(db, machine_id)

    stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.machine_id == machine.id)
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    )
    assessment = db.execute(stmt).scalar_one_or_none()
    if not assessment:
        return None

    return RiskAssessmentResponse(
        id=assessment.id,
        machine_id=assessment.machine_id,
        machine_name=machine.machine_id,
        prediction_id=assessment.prediction_id,
        risk_state=assessment.risk_state,
        health_index=assessment.health_index,
        predicted_rul=assessment.predicted_rul,
        reason_codes=assessment.reason_codes,
        explanation=assessment.explanation,
        policy_version=assessment.policy_version,
        evidence_references=assessment.evidence_references,
        created_at=assessment.created_at,
    )


@router.get(
    "/machines/{machine_id}/risk/history",
    response_model=RiskAssessmentListResponse,
    summary="Get paginated analytical risk history for an asset",
)
def get_risk_history(
    machine_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskAssessmentListResponse:
    """Returns paginated historical risk assessments for trend auditing."""
    machine = _resolve_machine(db, machine_id)

    base_stmt = select(RiskAssessment).where(RiskAssessment.machine_id == machine.id)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0

    stmt = (
        base_stmt
        .order_by(RiskAssessment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.execute(stmt).scalars().all())

    return RiskAssessmentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            RiskAssessmentResponse(
                id=a.id,
                machine_id=a.machine_id,
                machine_name=machine.machine_id,
                prediction_id=a.prediction_id,
                risk_state=a.risk_state,
                health_index=a.health_index,
                predicted_rul=a.predicted_rul,
                reason_codes=a.reason_codes,
                explanation=a.explanation,
                policy_version=a.policy_version,
                evidence_references=a.evidence_references,
                created_at=a.created_at,
            )
            for a in items
        ],
    )


@router.post(
    "/machines/{machine_id}/risk/evaluate",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate risk on demand from an empirical prediction",
)
def evaluate_machine_risk(
    machine_id: str,
    payload: Optional[RiskEvaluationRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> RiskAssessmentResponse:
    """
    Executes prediction inference (if needed), evaluates the deterministic risk engine,
    records any state transitions, and processes alert deduplication.
    """
    machine = _resolve_machine(db, machine_id)

    pred_svc = PredictionService(db)
    obs_cycle = payload.observation_cycle if payload else None
    model_version = payload.model_version if payload else None

    # Run inference and persist prediction
    prediction = pred_svc.predict_machine_health(
        machine_identifier=machine.machine_id,
        observation_cycle=obs_cycle,
        model_version=model_version,
        persist=True,
    )

    # Evaluate risk
    risk_engine = RiskEngine(db)
    assessment = risk_engine.evaluate_prediction(prediction, machine, persist=True)

    # Process alerts
    alert_service = AlertService(db)
    alert_service.process_risk_assessment(assessment, machine)

    return RiskAssessmentResponse(
        id=assessment.id,
        machine_id=assessment.machine_id,
        machine_name=machine.machine_id,
        prediction_id=assessment.prediction_id,
        risk_state=assessment.risk_state,
        health_index=assessment.health_index,
        predicted_rul=assessment.predicted_rul,
        reason_codes=assessment.reason_codes,
        explanation=assessment.explanation,
        policy_version=assessment.policy_version,
        evidence_references=assessment.evidence_references,
        created_at=assessment.created_at,
    )
