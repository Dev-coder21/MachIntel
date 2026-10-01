from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.core.errors import NotFoundException
from backend.app.models.machine import MachineStatus, MachineType, SplitCategory
from backend.app.models.user import User
from backend.app.repositories.machine_repository import MachineRepository
from backend.app.schemas.machine import (
    FoundationStatsResponse,
    MachineDetailRead,
    MachineListResponse,
    MachineRead,
)
from backend.app.schemas.telemetry import TelemetryCycleRead, TelemetryQueryResponse

router = APIRouter(prefix="/machines", tags=["Machine Registry & Telemetry"])


@router.get("/stats/summary", response_model=FoundationStatsResponse, summary="Get fleet and data foundation metrics")
def get_foundation_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FoundationStatsResponse:
    """Retrieve verified machine and telemetry ingestion statistics for the command center."""
    repo = MachineRepository(db)
    stats = repo.get_foundation_stats()
    return FoundationStatsResponse(**stats)


@router.get("", response_model=MachineListResponse, summary="List industrial machines with filtering and search")
def list_machines(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    machine_type: Optional[MachineType] = None,
    status_filter: Optional[MachineStatus] = Query(None, alias="status"),
    split_category: Optional[SplitCategory] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MachineListResponse:
    """Retrieve machines with bounded pagination, entity search, and lifecycle status filtering."""
    repo = MachineRepository(db)
    items, total = repo.list_machines(
        skip=skip,
        limit=limit,
        machine_type=machine_type,
        status=status_filter,
        split_category=split_category,
        search=search,
    )
    return MachineListResponse(
        items=[MachineRead.model_validate(m) for m in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{machine_id}", response_model=MachineDetailRead, summary="Get machine detail and provenance")
def get_machine(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MachineDetailRead:
    """Fetch machine profile, provenance dataset link, and channel specifications."""
    repo = MachineRepository(db)
    machine = repo.get_by_machine_id(machine_id)
    if not machine:
        raise NotFoundException(f"Machine with identifier '{machine_id}' not found")

    detail = MachineDetailRead.model_validate(machine)
    if machine.dataset:
        detail.active_sensor_channels = machine.dataset.active_sensors
        detail.invariant_sensor_channels = machine.dataset.invariant_sensors
    detail.quality_issues_count = len(machine.data_quality_issues)
    return detail


@router.get("/{machine_id}/telemetry", response_model=TelemetryQueryResponse, summary="Query bounded operational telemetry cycles")
def get_machine_telemetry(
    machine_id: str,
    start_cycle: Optional[int] = Query(None, ge=1, description="Starting flight cycle"),
    end_cycle: Optional[int] = Query(None, ge=1, description="Ending flight cycle"),
    limit: int = Query(100, ge=1, le=500, description="Max cycles to return per request"),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TelemetryQueryResponse:
    """Query bounded, cycle-ordered sensor telemetry records without synthetic timestamps."""
    repo = MachineRepository(db)
    machine = repo.get_by_machine_id(machine_id)
    if not machine:
        raise NotFoundException(f"Machine with identifier '{machine_id}' not found")

    records, total, min_c, max_c = repo.get_telemetry_cycles(
        machine_id=machine.id,
        start_cycle=start_cycle,
        end_cycle=end_cycle,
        limit=limit,
        offset=offset,
    )

    effective_start = start_cycle if start_cycle is not None else min_c
    effective_end = end_cycle if end_cycle is not None else max_c

    return TelemetryQueryResponse(
        machine_id=machine.machine_id,
        total_records=total,
        min_cycle=min_c,
        max_cycle=max_c,
        start_cycle=effective_start,
        end_cycle=effective_end,
        returned_records=len(records),
        records=[TelemetryCycleRead.model_validate(r) for r in records],
    )
