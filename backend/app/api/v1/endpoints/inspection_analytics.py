import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.inspection import InspectionRunResponse
from backend.app.schemas.inspection_analytics import (
    ConfusionMatrixAnalyticsResponse,
    DefectClassAnalyticsResponse,
    InspectionRunAnalyticsSummaryResponse,
    InspectionRunProvenanceResponse,
    LocalizationAnalyticsResponse,
    RunComparisonResponse,
    ScoreDistributionResponse,
)
from backend.app.services.inspection_analytics_service import InspectionAnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inspection-analytics", tags=["Inspection Analytics"])


@router.get(
    "/runs",
    response_model=List[InspectionRunResponse],
    summary="List inspection runs with filtering",
)
def list_inspection_runs(
    dataset_identifier: Optional[str] = Query(None, description="Filter by dataset identifier"),
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    policy_version: Optional[str] = Query(None, description="Filter by policy version"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[InspectionRunResponse]:
    svc = InspectionAnalyticsService(db)
    runs = svc.list_runs(
        dataset_identifier=dataset_identifier,
        model_version=model_version,
        policy_version=policy_version,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return [InspectionRunResponse.model_validate(r) for r in runs]


@router.get(
    "/runs/{run_id}/summary",
    response_model=InspectionRunAnalyticsSummaryResponse,
    summary="Get comprehensive statistical run summary",
)
def get_run_summary(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InspectionRunAnalyticsSummaryResponse:
    svc = InspectionAnalyticsService(db)
    return svc.get_run_summary(run_id)


@router.get(
    "/runs/{run_id}/scores",
    response_model=ScoreDistributionResponse,
    summary="Get anomaly score distribution histogram and percentiles",
)
def get_score_distribution(
    run_id: uuid.UUID,
    bins: int = Query(15, ge=5, le=50, description="Number of histogram bins"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreDistributionResponse:
    svc = InspectionAnalyticsService(db)
    return svc.get_score_distribution(run_id, num_bins=bins)


@router.get(
    "/runs/{run_id}/defects",
    response_model=DefectClassAnalyticsResponse,
    summary="Get category-level defect detection analytics",
)
def get_defect_class_analytics(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DefectClassAnalyticsResponse:
    svc = InspectionAnalyticsService(db)
    return svc.get_defect_class_analytics(run_id)


@router.get(
    "/runs/{run_id}/confusion-matrix",
    response_model=ConfusionMatrixAnalyticsResponse,
    summary="Get confusion matrix and classification metrics",
)
def get_confusion_matrix(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConfusionMatrixAnalyticsResponse:
    svc = InspectionAnalyticsService(db)
    return svc.get_confusion_matrix_analytics(run_id)


@router.get(
    "/runs/{run_id}/localization",
    response_model=LocalizationAnalyticsResponse,
    summary="Get pixel-level localization metrics",
)
def get_localization_analytics(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocalizationAnalyticsResponse:
    svc = InspectionAnalyticsService(db)
    return svc.get_localization_analytics(run_id)


@router.get(
    "/runs/{run_id}/provenance",
    response_model=InspectionRunProvenanceResponse,
    summary="Get inspection run cryptographic and model provenance",
)
def get_run_provenance(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InspectionRunProvenanceResponse:
    svc = InspectionAnalyticsService(db)
    return svc.get_run_provenance(run_id)


@router.get(
    "/compare",
    response_model=RunComparisonResponse,
    summary="Compare real inspection runs across models and policies",
)
def compare_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunComparisonResponse:
    svc = InspectionAnalyticsService(db)
    return svc.compare_runs()
