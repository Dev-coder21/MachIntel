from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.core.risk_policy import AlertSeverity, AlertStatus
from backend.app.models.alert import Alert
from backend.app.models.user import User, UserRole
from backend.app.schemas.alert import (
    AlertActionRequest,
    AlertListResponse,
    AlertResponse,
    AlertSummaryResponse,
)
from backend.app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts & Operational Lifecycle"])


def _format_alert_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        machine_id=alert.machine_id,
        machine_name=alert.machine.machine_id if alert.machine else None,
        risk_assessment_id=alert.risk_assessment_id,
        severity=alert.severity,
        status=alert.status,
        title=alert.title,
        description=alert.description,
        reason_codes=alert.reason_codes,
        deduplication_key=alert.deduplication_key,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        acknowledged_by_username=alert.acknowledged_by.username if alert.acknowledged_by else None,
        resolved_by_username=alert.resolved_by.username if alert.resolved_by else None,
    )


@router.get(
    "/summary",
    response_model=AlertSummaryResponse,
    summary="Get fleet-wide alert summary metrics",
)
def get_alert_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertSummaryResponse:
    """Returns open, acknowledged, and resolved alert counts categorized by severity."""
    svc = AlertService(db)
    summary_data = svc.get_alert_summary()
    return AlertSummaryResponse(**summary_data)


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List operational alerts with filtering and pagination",
)
def list_alerts(
    status_filter: Optional[AlertStatus] = Query(None, alias="status"),
    severity_filter: Optional[AlertSeverity] = Query(None, alias="severity"),
    machine_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertListResponse:
    """Lists alerts with bounded pagination, status filters, and machine search."""
    svc = AlertService(db)
    items, total = svc.list_alerts(
        status_filter=status_filter.value if status_filter else None,
        severity_filter=severity_filter.value if severity_filter else None,
        machine_id=machine_id,
        page=page,
        page_size=page_size,
    )
    return AlertListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_format_alert_response(a) for a in items],
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get details for a specific alert",
)
def get_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertResponse:
    """Returns alert details, reason codes, and provenance."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    return _format_alert_response(alert)


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an open alert (Operator/Admin)",
)
def acknowledge_alert(
    alert_id: uuid.UUID,
    payload: Optional[AlertActionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> AlertResponse:
    """Transitions alert status from OPEN to ACKNOWLEDGED with audit logging."""
    svc = AlertService(db)
    comment = payload.comment if payload else None
    alert = svc.acknowledge_alert(alert_id, actor=current_user, comment=comment)
    return _format_alert_response(alert)


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Resolve an alert (Operator/Admin)",
)
def resolve_alert(
    alert_id: uuid.UUID,
    payload: Optional[AlertActionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> AlertResponse:
    """Transitions alert status to RESOLVED with audit logging."""
    svc = AlertService(db)
    comment = payload.comment if payload else None
    alert = svc.resolve_alert(alert_id, actor=current_user, comment=comment)
    return _format_alert_response(alert)
