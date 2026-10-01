from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.ai_investigation import AIInvestigation
from backend.app.models.user import User, UserRole
from backend.app.schemas.ai_investigation import (
    AIInvestigationResponse,
    AIInvestigationSummary,
    InvestigationCreateRequest,
    ToolDefinitionSchema,
)
from backend.app.services.ai_inspector.orchestrator import InvestigationOrchestrator
from backend.app.services.ai_inspector.tools import tool_registry

router = APIRouter(prefix="/ai-inspector", tags=["AI Inspector (Forensics)"])


@router.post(
    "/investigations",
    response_model=AIInvestigationResponse,
    summary="Execute evidence-grounded AI forensic investigation",
)
async def create_investigation(
    payload: InvestigationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIInvestigationResponse:
    """
    Submits a natural-language inquiry to the AI Inspector.
    Executes controlled read-only tools against real telemetry, risk, inspection,
    and maintenance evidence, synthesizing a structured and validated response.
    """
    orchestrator = InvestigationOrchestrator(db=db)
    return await orchestrator.execute_investigation(
        question=payload.question,
        current_user=current_user,
        context=payload.context,
    )


@router.get(
    "/investigations",
    response_model=List[AIInvestigationSummary],
    summary="List past investigations for authenticated user",
)
def list_investigations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AIInvestigationSummary]:
    """Retrieves chronological investigation history."""
    query = select(AIInvestigation)
    # Non-admins only see their own investigations
    if current_user.role != UserRole.ADMIN:
        query = query.where(AIInvestigation.user_id == current_user.id)

    if status_filter:
        query = query.where(AIInvestigation.status == status_filter.upper())

    query = query.order_by(desc(AIInvestigation.started_at)).offset(offset).limit(limit)
    records = db.execute(query).scalars().all()

    return [
        AIInvestigationSummary(
            id=r.id,
            question=r.question,
            status=r.status,
            provider=r.provider,
            model=r.model,
            domains_consulted=r.domains_consulted or [],
            evidence_count=len(r.evidence_ids_referenced or []),
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in records
    ]


@router.get(
    "/investigations/{investigation_id}",
    response_model=AIInvestigationResponse,
    summary="Get detailed investigation results and evidence trace",
)
def get_investigation(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIInvestigationResponse:
    """Retrieves full investigation response and tool execution trace by UUID."""
    r = db.get(AIInvestigation, investigation_id)
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found.",
        )

    if current_user.role != UserRole.ADMIN and r.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden to this investigation.",
        )

    if r.structured_response:
        return AIInvestigationResponse.model_validate(r.structured_response)

    # Fallback reconstruction if structured_response not populated
    return AIInvestigationResponse(
        id=r.id,
        question=r.question,
        status=r.status,
        answer="",
        evidence=[],
        limitations=[],
        investigation={"tool_calls": r.tool_calls or [], "domains_consulted": r.domains_consulted or [], "completed": True},
        provider=r.provider,
        model=r.model,
        created_at=r.started_at,
        completed_at=r.completed_at,
        error_message=r.error_message,
    )


@router.get(
    "/tools",
    response_model=List[ToolDefinitionSchema],
    summary="List registered read-only AI Inspector tools and input schemas",
)
def list_inspector_tools(
    current_user: User = Depends(get_current_user),
) -> List[ToolDefinitionSchema]:
    """Returns documentation and schemas for all active, read-only investigation tools."""
    tools = tool_registry.list_tools()
    return [
        ToolDefinitionSchema(
            name=t.name,
            description=t.description,
            domain=t.domain,
            read_only=t.read_only,
            parameters=t.input_schema,
        )
        for t in tools
    ]
