from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.analytics import (
    CorrelationMatrixResponse,
    FeaturePreviewResponse,
    FleetAnalyticsOverviewResponse,
    MachineAnalyticsSummary,
    MachineComparisonResponse,
    SensorSummaryItem,
    SensorTrendResponse,
)
from backend.app.services.analytics_service import MachineAnalyticsService

router = APIRouter(tags=["Machine Analytics & Feature Engineering"])


@router.get(
    "/machines/analytics/overview",
    response_model=FleetAnalyticsOverviewResponse,
    summary="Get fleet-wide operational telemetry coverage and cycle distributions",
)
def get_fleet_analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FleetAnalyticsOverviewResponse:
    """Provides fleet operational analytics without risk or prediction fabrication."""
    service = MachineAnalyticsService(db)
    return service.get_fleet_analytics_overview()


@router.get(
    "/machines/analytics/compare",
    response_model=MachineComparisonResponse,
    summary="Compare operational telemetry metrics across multiple machines",
)
def compare_machines(
    machine_ids: str = Query(
        ...,
        description="Comma-separated machine identifiers (e.g. 'TURBOFAN-ENG-001,TURBOFAN-ENG-002')",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MachineComparisonResponse:
    """Performs analytical comparisons (drift, cycles, volatility) across selected machines."""
    ids = [m.strip() for m in machine_ids.split(",") if m.strip()]
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one machine identifier must be provided for comparison.",
        )
    if len(ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Machine comparison is bounded to at most 10 machines.",
        )
    service = MachineAnalyticsService(db)
    return service.compare_machines(ids)


@router.get(
    "/machines/{machine_id}/analytics/summary",
    response_model=MachineAnalyticsSummary,
    summary="Get machine operational telemetry analytics summary",
)
def get_machine_analytics_summary(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MachineAnalyticsSummary:
    """Computes comprehensive sensor summaries, top drifting channels, and cycle coverage."""
    service = MachineAnalyticsService(db)
    return service.get_summary(machine_id)


@router.get(
    "/machines/{machine_id}/analytics/sensors",
    response_model=List[SensorSummaryItem],
    summary="Get statistical summary across all active sensor channels",
)
def get_machine_sensor_analytics(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SensorSummaryItem]:
    """Retrieves min, max, mean, std, initial, latest, and directional drift for each active channel."""
    service = MachineAnalyticsService(db)
    return service.get_sensors(machine_id)


@router.get(
    "/machines/{machine_id}/analytics/trends",
    response_model=SensorTrendResponse,
    summary="Get rolling window trend analysis for a specific active sensor channel",
)
def get_machine_sensor_trends(
    machine_id: str,
    sensor: str = Query(..., description="Active sensor key (e.g. 'sensor_2', 'sensor_3', 'sensor_7')"),
    window: int = Query(20, ge=2, le=100, description="Rolling window size in cycles (default: 20)"),
    max_points: int = Query(300, ge=20, le=1000, description="Maximum points returned (downsampled if needed)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SensorTrendResponse:
    """
    Computes temporally causal rolling mean, rolling std, rolling min/max, and OLS rolling slope.
    Strictly forbids future lookahead or cross-machine leakage.
    """
    service = MachineAnalyticsService(db)
    return service.get_trends(machine_id, sensor=sensor, window=window, max_points=max_points)


@router.get(
    "/machines/{machine_id}/analytics/correlation",
    response_model=CorrelationMatrixResponse,
    summary="Get Pearson correlation matrix across active sensor channels",
)
def get_machine_sensor_correlation(
    machine_id: str,
    channels: Optional[List[str]] = Query(None, description="Subset of active channels (defaults to key sensors)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CorrelationMatrixResponse:
    """Computes bivariate Pearson correlation matrix between active sensor channels for an asset."""
    service = MachineAnalyticsService(db)
    return service.get_correlation(machine_id, channels=channels)


@router.get(
    "/machines/{machine_id}/analytics/features",
    response_model=FeaturePreviewResponse,
    summary="Preview derived ML features under the Milestone M4 contract",
)
def get_machine_feature_preview(
    machine_id: str,
    start_cycle: int = Query(1, ge=1, le=1000, description="Start cycle for feature preview"),
    end_cycle: int = Query(50, ge=1, le=1000, description="End cycle for feature preview"),
    window: int = Query(20, ge=2, le=50, description="Rolling window size (default: 20)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeaturePreviewResponse:
    """
    Returns exact derived features that the Phase 4 ML RUL model will consume.
    Explicitly annotated as derived features with zero synthetic predictions.
    """
    if end_cycle < start_cycle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_cycle must be greater than or equal to start_cycle.",
        )
    service = MachineAnalyticsService(db)
    return service.get_feature_preview(
        machine_id,
        start_cycle=start_cycle,
        end_cycle=end_cycle,
        window=window,
    )
