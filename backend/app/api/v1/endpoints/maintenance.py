from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.inspection import InspectionResult
from backend.app.models.risk import RiskAssessment
from backend.app.models.user import User, UserRole
from backend.app.schemas.maintenance import (
    MaintenanceEventResponse,
    MaintenancePriority,
    MaintenanceSourceDomain,
    MaintenanceStatus,
    MaintenanceSummaryResponse,
    MaintenanceWorkOrderDetailResponse,
    MaintenanceWorkOrderResponse,
    MaintenanceWorkOrderCreate,
    WorkOrderAcknowledgeRequest,
    WorkOrderCancelRequest,
    WorkOrderCompleteRequest,
    WorkOrderStartRequest,
)
from backend.app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["Maintenance Operations"])


def _format_work_order(wo) -> MaintenanceWorkOrderResponse:
    return MaintenanceWorkOrderResponse(
        id=wo.id,
        machine_id=wo.machine_id,
        source_domain=wo.source_domain,
        source_type=wo.source_type,
        source_reference=wo.source_reference,
        deduplication_key=wo.deduplication_key,
        title=wo.title,
        description=wo.description,
        priority=wo.priority,
        status=wo.status,
        recommended_action=wo.recommended_action,
        reason=wo.reason,
        risk_state_at_creation=wo.risk_state_at_creation,
        predicted_rul_at_creation=wo.predicted_rul_at_creation,
        health_index_at_creation=wo.health_index_at_creation,
        anomaly_score_at_creation=wo.anomaly_score_at_creation,
        policy_version=wo.policy_version,
        evidence_references=wo.evidence_references or [],
        created_by_id=wo.created_by_id,
        assigned_to_id=wo.assigned_to_id,
        created_at=wo.created_at,
        acknowledged_at=wo.acknowledged_at,
        started_at=wo.started_at,
        completed_at=wo.completed_at,
        cancelled_at=wo.cancelled_at,
        updated_at=wo.updated_at,
        resolution_notes=wo.resolution_notes,
    )


@router.get(
    "/summary",
    response_model=MaintenanceSummaryResponse,
    summary="Get fleet-wide maintenance KPIs and recent activity",
)
def get_maintenance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MaintenanceSummaryResponse:
    """Returns counts of active, completed, cancelled, and priority-bucketed work orders."""
    data = MaintenanceService.get_summary(db)
    return MaintenanceSummaryResponse(
        total_work_orders=data["total_work_orders"],
        open_count=data["open_count"],
        acknowledged_count=data["acknowledged_count"],
        in_progress_count=data["in_progress_count"],
        completed_count=data["completed_count"],
        cancelled_count=data["cancelled_count"],
        critical_priority_count=data["critical_priority_count"],
        high_priority_count=data["high_priority_count"],
        medium_priority_count=data["medium_priority_count"],
        low_priority_count=data["low_priority_count"],
        machine_health_count=data["machine_health_count"],
        visual_inspection_count=data["visual_inspection_count"],
        recent_activity=[
            MaintenanceEventResponse.model_validate(e) for e in data["recent_activity"]
        ],
    )


@router.get(
    "/work-orders",
    response_model=List[MaintenanceWorkOrderResponse],
    summary="List maintenance work orders with filtering and pagination",
)
def list_work_orders(
    status: Optional[str] = Query(None, description="Filter by status (OPEN, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, CANCELLED)"),
    priority: Optional[str] = Query(None, description="Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)"),
    source_domain: Optional[str] = Query(None, description="Filter by source domain (MACHINE_HEALTH, VISUAL_INSPECTION)"),
    machine_id: Optional[str] = Query(None, description="Filter by asset machine identifier"),
    created_by: Optional[uuid.UUID] = Query(None, description="Filter by creator user ID"),
    assigned_to: Optional[uuid.UUID] = Query(None, description="Filter by assignee user ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MaintenanceWorkOrderResponse]:
    items, _ = MaintenanceService.list_work_orders(
        db=db,
        status_filter=status,
        priority_filter=priority,
        source_domain_filter=source_domain,
        machine_id_filter=machine_id,
        created_by_id=created_by,
        assigned_to_id=assigned_to,
        skip=skip,
        limit=limit,
    )
    return [_format_work_order(item) for item in items]


@router.get(
    "/work-orders/{work_order_id}",
    response_model=MaintenanceWorkOrderDetailResponse,
    summary="Get single work order with event history and source details",
)
def get_work_order_detail(
    work_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MaintenanceWorkOrderDetailResponse:
    wo = MaintenanceService.get_work_order(db, work_order_id)
    base = _format_work_order(wo)

    # Fetch source entity details for rich inspection/health display
    source_details: Optional[Dict[str, Any]] = None
    try:
        source_uuid = uuid.UUID(wo.source_reference)
        if wo.source_domain == MaintenanceSourceDomain.MACHINE_HEALTH.value:
            if wo.source_type == "RISK_ASSESSMENT":
                assessment = db.get(RiskAssessment, source_uuid)
                if assessment:
                    source_details = {
                        "risk_state": assessment.risk_state,
                        "predicted_rul": assessment.predicted_rul,
                        "health_index": assessment.health_index,
                        "cycle": assessment.prediction.observation_cycle if assessment.prediction else None,
                        "reason_codes": assessment.reason_codes,
                        "evaluated_at": assessment.created_at.isoformat() if assessment.created_at else None,
                    }
        elif wo.source_domain == MaintenanceSourceDomain.VISUAL_INSPECTION.value:
            if wo.source_type == "INSPECTION_RESULT":
                result = db.get(InspectionResult, source_uuid)
                if result:
                    source_details = {
                        "decision": result.decision,
                        "defect_type": result.defect_class,
                        "anomaly_score": result.image_level_score,
                        "threshold": result.run.threshold if result.run else 0.5,
                        "image_path": result.source_image_path,
                        "has_localization": bool(result.heatmap_path or result.overlay_path),
                    }
    except Exception:
        source_details = None

    return MaintenanceWorkOrderDetailResponse(
        **base.model_dump(),
        events=[MaintenanceEventResponse.model_validate(e) for e in wo.events],
        source_entity_details=source_details,
    )


@router.post(
    "/work-orders",
    response_model=MaintenanceWorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new maintenance work order",
)
def create_work_order(
    payload: MaintenanceWorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> MaintenanceWorkOrderResponse:
    """Explicitly creates a work order or returns existing active item via deduplication."""
    wo, _ = MaintenanceService.create_work_order(db, payload, current_user)
    return _format_work_order(wo)


@router.post(
    "/recommendations/from-risk/{risk_id}",
    response_model=MaintenanceWorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Draft maintenance recommendation from RiskAssessment",
)
def draft_recommendation_from_risk(
    risk_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> MaintenanceWorkOrderResponse:
    """Drafts an OPEN maintenance work item from an authentic RiskAssessment record."""
    wo, _ = MaintenanceService.recommend_from_risk(db, risk_id, current_user)
    return _format_work_order(wo)


@router.post(
    "/recommendations/from-inspection/{inspection_result_id}",
    response_model=MaintenanceWorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Draft maintenance recommendation from InspectionResult",
)
def draft_recommendation_from_inspection(
    inspection_result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> MaintenanceWorkOrderResponse:
    """Drafts an OPEN maintenance work item from an authentic DEFECT InspectionResult."""
    wo, _ = MaintenanceService.recommend_from_inspection(db, inspection_result_id, current_user)
    return _format_work_order(wo)


@router.post(
    "/work-orders/{id}/acknowledge",
    response_model=MaintenanceWorkOrderResponse,
    summary="Acknowledge an open work order",
)
def acknowledge_work_order(
    id: uuid.UUID,
    req: WorkOrderAcknowledgeRequest = WorkOrderAcknowledgeRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> MaintenanceWorkOrderResponse:
    wo = MaintenanceService.acknowledge_work_order(
        db=db,
        work_order_id=id,
        actor=current_user,
        assigned_to_id=req.assigned_to_id,
        notes=req.notes,
    )
    return _format_work_order(wo)


@router.post(
    "/work-orders/{id}/start",
    response_model=MaintenanceWorkOrderResponse,
    summary="Mark work order as in-progress",
)
def start_work_order(
    id: uuid.UUID,
    req: WorkOrderStartRequest = WorkOrderStartRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> MaintenanceWorkOrderResponse:
    wo = MaintenanceService.start_work_order(
        db=db,
        work_order_id=id,
        actor=current_user,
        notes=req.notes,
    )
    return _format_work_order(wo)


@router.post(
    "/work-orders/{id}/complete",
    response_model=MaintenanceWorkOrderResponse,
    summary="Complete work order with human-verified resolution notes",
)
def complete_work_order(
    id: uuid.UUID,
    req: WorkOrderCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> MaintenanceWorkOrderResponse:
    wo = MaintenanceService.complete_work_order(
        db=db,
        work_order_id=id,
        actor=current_user,
        resolution_notes=req.resolution_notes,
        notes=req.notes,
    )
    return _format_work_order(wo)


@router.post(
    "/work-orders/{id}/cancel",
    response_model=MaintenanceWorkOrderResponse,
    summary="Cancel work order with recorded reason",
)
def cancel_work_order(
    id: uuid.UUID,
    req: WorkOrderCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> MaintenanceWorkOrderResponse:
    wo = MaintenanceService.cancel_work_order(
        db=db,
        work_order_id=id,
        actor=current_user,
        reason=req.reason,
        notes=req.notes,
    )
    return _format_work_order(wo)
