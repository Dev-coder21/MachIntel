import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.models.prediction import OperationalState


class PredictionCreateRequest(BaseModel):
    observation_cycle: Optional[int] = Field(
        None,
        description="Specific observation cycle to run inference on. If omitted, uses the latest available cycle for this engine.",
    )
    model_version: Optional[str] = Field(
        None,
        description="Model ID to use (e.g. 'rul-randomforest-v1.0.0'). If omitted, uses the currently active model.",
    )


class PredictionResponse(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: Optional[str] = None
    model_version: str
    dataset_version: str
    feature_version: str
    observation_cycle: int
    predicted_rul: float = Field(..., ge=0.0, description="Estimated Remaining Useful Life in cycles (non-negative)")
    health_index: float = Field(..., ge=0.0, le=1.0, description="Normalized Health Index [0.0, 1.0]")
    operational_state: OperationalState = Field(..., description="Derived analytical risk state")
    created_at: datetime
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class PredictionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PredictionResponse]


class FleetPrognosticsOverview(BaseModel):
    total_machines: int
    machines_with_predictions: int
    active_model_id: str
    active_model_algorithm: str
    average_predicted_rul: Optional[float]
    average_health_index: Optional[float]
    state_distribution: Dict[str, int]
