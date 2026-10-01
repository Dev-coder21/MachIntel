from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from backend.app.models.machine import MachineStatus, MachineType, SplitCategory
from backend.app.schemas.dataset import DatasetMetadataRead


class MachineBase(BaseModel):
    machine_id: str = Field(..., description="Unique industrial asset identifier (e.g. TURBOFAN-ENG-001)")
    name: str = Field(..., description="Human-readable asset title")
    machine_type: MachineType = Field(default=MachineType.TURBOFAN_ENGINE)
    source_dataset: str = Field(..., description="Originating dataset family")
    source_entity_id: str = Field(..., description="Source system entity identifier")
    status: MachineStatus = Field(default=MachineStatus.OPERATIONAL)
    split_category: SplitCategory = Field(default=SplitCategory.INTERNAL_TRAIN)


class MachineRead(MachineBase):
    id: uuid.UUID
    dataset_id: Optional[uuid.UUID] = None
    total_cycles: int
    max_cycle: int
    ground_truth_rul: Optional[int] = None
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MachineDetailRead(MachineRead):
    dataset: Optional[DatasetMetadataRead] = None
    active_sensor_channels: List[str] = Field(default_factory=list)
    invariant_sensor_channels: List[str] = Field(default_factory=list)
    quality_issues_count: int = 0


class MachineListResponse(BaseModel):
    items: List[MachineRead]
    total: int
    skip: int
    limit: int


class FoundationStatsResponse(BaseModel):
    total_machines: int
    total_telemetry_records: int
    operational_count: int
    degraded_count: int
    maintenance_count: int
    datasets_registered: int
