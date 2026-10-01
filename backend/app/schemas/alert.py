from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from backend.app.core.risk_policy import AlertSeverity, AlertStatus


class AlertResponse(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: Optional[str] = None
    risk_assessment_id: uuid.UUID
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    reason_codes: List[str]
    deduplication_key: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by_username: Optional[str] = None
    resolved_by_username: Optional[str] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AlertResponse]


class AlertSummaryResponse(BaseModel):
    total_alerts: int
    open_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int
    critical_open_alerts: int
    warning_open_alerts: int
    info_open_alerts: int
    by_severity: Dict[str, int]
    by_status: Dict[str, int]


class AlertActionRequest(BaseModel):
    comment: Optional[str] = Field(None, description="Optional operator comment or resolution reason")
