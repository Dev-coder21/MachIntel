from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.dataset import DatasetMetadata


class DatasetRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_datasets(self) -> List[DatasetMetadata]:
        return list(
            self.db.execute(
                select(DatasetMetadata).order_by(DatasetMetadata.created_at.desc())
            ).scalars().all()
        )

    def get_by_id_or_name(self, id_or_name: str) -> Optional[DatasetMetadata]:
        try:
            val_uuid = uuid.UUID(id_or_name)
            return self.db.execute(
                select(DatasetMetadata).where(DatasetMetadata.id == val_uuid)
            ).scalar_one_or_none()
        except ValueError:
            return self.db.execute(
                select(DatasetMetadata).where(DatasetMetadata.dataset_name == id_or_name.strip())
            ).scalar_one_or_none()
