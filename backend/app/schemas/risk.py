from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from backend.app.core.risk_policy import RiskState


class RiskAssessmentResponse(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: Optional[str] = None
    prediction_id: uuid.UUID
    risk_state: RiskState
    health_index: float = Field(..., ge=0.0, le=1.0)
    predicted_rul: float = Field(..., ge=0.0)
    reason_codes: List[str]
    explanation: str
    policy_version: str
    evidence_references: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class RiskAssessmentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[RiskAssessmentResponse]


class RiskTransitionResponse(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: Optional[str] = None
    from_state: str
    to_state: str
    observation_cycle: int
    created_at: datetime

    class Config:
        from_attributes = True


class RiskEvaluationRequest(BaseModel):
    observation_cycle: Optional[int] = Field(
        None,
        description="Optional observation cycle to evaluate. Defaults to the latest available cycle.",
    )
    model_version: Optional[str] = Field(
        None,
        description="Optional model ID to use. Defaults to the currently active serving model.",
    )
