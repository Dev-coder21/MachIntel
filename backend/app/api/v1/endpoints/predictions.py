from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.user import User, UserRole
from backend.app.schemas.prediction import (
    FleetPrognosticsOverview,
    PredictionCreateRequest,
    PredictionListResponse,
    PredictionResponse,
)
from backend.app.services.prediction_service import PredictionService

router = APIRouter(tags=["Prognostics & RUL Predictions"])


@router.get(
    "/predictions/fleet/overview",
    response_model=FleetPrognosticsOverview,
    summary="Get fleet-wide prognostic summary and health state distribution",
)
def get_fleet_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FleetPrognosticsOverview:
    """Aggregates latest real predictions across machines to compute fleet health state distribution and coverage."""
    svc = PredictionService(db)
    overview = svc.get_fleet_overview()
    return FleetPrognosticsOverview(**overview)


@router.post(
    "/machines/{machine_id}/predictions",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run real RUL inference and persist prognostic prediction",
)
def create_machine_prediction(
    machine_id: str,
    payload: Optional[PredictionCreateRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
) -> PredictionResponse:
    """
    Executes actual causal inference using trained baseline models (RandomForest or Ridge).
    Extracts rolling features up to observation cycle, transforms via training-fitted scaler,
    predicts RUL, clamps non-negative, and calculates deterministic Health Index.
    """
    svc = PredictionService(db)
    obs_cycle = payload.observation_cycle if payload else None
    model_version = payload.model_version if payload else None

    prediction = svc.predict_machine_health(
        machine_identifier=machine_id,
        observation_cycle=obs_cycle,
        model_version=model_version,
        persist=True,
    )

    return PredictionResponse(
        id=prediction.id,
        machine_id=prediction.machine_id,
        machine_name=prediction.machine.machine_id if prediction.machine else machine_id,
        model_version=prediction.model_version.model_id if prediction.model_version else (model_version or "unknown"),
        dataset_version=prediction.dataset.dataset_name if prediction.dataset else "NASA-C-MAPSS-FD001",
        feature_version=prediction.feature_engineering_version,
        observation_cycle=prediction.observation_cycle,
        predicted_rul=prediction.predicted_rul,
        health_index=prediction.health_index,
        operational_state=prediction.operational_state,
        created_at=prediction.created_at,
        metadata_json=prediction.metadata_json,
    )


@router.get(
    "/machines/{machine_id}/predictions/latest",
    response_model=Optional[PredictionResponse],
    summary="Get latest prognostic prediction for a machine",
)
def get_latest_prediction(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Optional[PredictionResponse]:
    """Retrieves the most recent persisted prediction for the designated engine."""
    svc = PredictionService(db)
    prediction = svc.get_latest_prediction(machine_id)
    if not prediction:
        return None

    return PredictionResponse(
        id=prediction.id,
        machine_id=prediction.machine_id,
        machine_name=prediction.machine.machine_id if prediction.machine else machine_id,
        model_version=prediction.model_version.model_id if prediction.model_version else "unknown",
        dataset_version=prediction.dataset.dataset_name if prediction.dataset else "NASA-C-MAPSS-FD001",
        feature_version=prediction.feature_engineering_version,
        observation_cycle=prediction.observation_cycle,
        predicted_rul=prediction.predicted_rul,
        health_index=prediction.health_index,
        operational_state=prediction.operational_state,
        created_at=prediction.created_at,
        metadata_json=prediction.metadata_json,
    )


@router.get(
    "/machines/{machine_id}/predictions",
    response_model=PredictionListResponse,
    summary="Get paginated prediction history for a machine",
)
def get_prediction_history(
    machine_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PredictionListResponse:
    """Returns paginated prediction history for trend analysis and degradation tracking."""
    svc = PredictionService(db)
    items, total = svc.get_prediction_history(machine_id, page=page, page_size=page_size)

    formatted = [
        PredictionResponse(
            id=p.id,
            machine_id=p.machine_id,
            machine_name=p.machine.machine_id if p.machine else machine_id,
            model_version=p.model_version.model_id if p.model_version else "unknown",
            dataset_version=p.dataset.dataset_name if p.dataset else "NASA-C-MAPSS-FD001",
            feature_version=p.feature_engineering_version,
            observation_cycle=p.observation_cycle,
            predicted_rul=p.predicted_rul,
            health_index=p.health_index,
            operational_state=p.operational_state,
            created_at=p.created_at,
            metadata_json=p.metadata_json,
        )
        for p in items
    ]

    return PredictionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=formatted,
    )
