from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class InvestigationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    machine_id: Optional[str] = Field(None, max_length=100, description="Optional target machine identifier")
    inspection_run_id: Optional[uuid.UUID] = Field(None, description="Optional target visual inspection run UUID")
    inspection_result_id: Optional[uuid.UUID] = Field(None, description="Optional target visual inspection result UUID")
    domain: Optional[str] = Field(None, description="Optional preferred evidence domain: MACHINE_HEALTH or VISUAL_INSPECTION")


class InvestigationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=3, max_length=1000, description="Natural language investigation query")
    context: Optional[InvestigationContext] = Field(default=None, description="Optional entity context for grounding")


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: str = Field(..., description="UUID or identifier of authoritative EvidenceRecord")
    domain: str = Field(..., description="Domain: MACHINE_HEALTH or VISUAL_INSPECTION")
    type: str = Field(..., description="Evidence type (e.g. PREDICTION, RISK_ASSESSMENT, INSPECTION_RESULT)")
    source: str = Field(..., description="Origin source system (e.g. C-MAPSS_FD001, MVTEC_AD_METALNUT)")
    observation_cycle: Optional[int] = Field(None, description="Observation cycle where applicable")
    quality_state: str = Field(..., description="Quality certification: VERIFIED, SUSPECT, INVALID")
    explanation: Optional[str] = Field(None, description="Why this evidence supports the finding")
    value_summary: Optional[str] = Field(None, description="Key numerical or categorical metrics snapshot")


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # SUCCESS, FAILED, TIMEOUT
    duration_ms: float
    evidence_ids_returned: List[str] = Field(default_factory=list)


class InvestigationTrace(BaseModel):
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    domains_consulted: List[str] = Field(default_factory=list)
    completed: bool = True


class AIInvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    status: str  # COMPLETED, FAILED, PROVIDER_UNAVAILABLE
    answer: str
    evidence: List[EvidenceCitation] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    investigation: InvestigationTrace
    provider: str
    model: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AIInvestigationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    status: str
    provider: str
    model: str
    domains_consulted: List[str]
    evidence_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class ToolDefinitionSchema(BaseModel):
    name: str
    description: str
    domain: str
    read_only: bool = True
    parameters: Dict[str, Any]
