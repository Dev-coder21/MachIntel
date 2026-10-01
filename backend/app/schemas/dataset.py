from datetime import datetime
from typing import Any, Dict, List
import uuid
from pydantic import BaseModel, Field


class DatasetMetadataRead(BaseModel):
    id: uuid.UUID
    dataset_name: str
    dataset_identifier: str
    source: str
    source_url: str
    license: str
    retrieval_date: datetime
    file_checksums: Dict[str, Any]
    schema_version: str
    preprocessing_version: str
    ingestion_version: str
    active_sensors: List[str]
    invariant_sensors: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    items: List[DatasetMetadataRead]
    total: int
