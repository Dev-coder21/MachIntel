from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.core.errors import NotFoundException
from backend.app.models.user import User
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.schemas.dataset import DatasetListResponse, DatasetMetadataRead

router = APIRouter(prefix="/datasets", tags=["Dataset Provenance & Metadata"])


@router.get("", response_model=DatasetListResponse, summary="List registered datasets and provenance metadata")
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetListResponse:
    """Retrieve all formal dataset provenance records."""
    repo = DatasetRepository(db)
    datasets = repo.list_datasets()
    return DatasetListResponse(
        items=[DatasetMetadataRead.model_validate(d) for d in datasets],
        total=len(datasets),
    )


@router.get("/{dataset_id}", response_model=DatasetMetadataRead, summary="Get dataset metadata by UUID or identifier")
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetMetadataRead:
    """Fetch specific dataset provenance specifications and checksums."""
    repo = DatasetRepository(db)
    meta = repo.get_by_id_or_name(dataset_id)
    if not meta:
        raise NotFoundException(f"Dataset with identifier '{dataset_id}' not found")
    return DatasetMetadataRead.model_validate(meta)
