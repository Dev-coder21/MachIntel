from typing import List, Optional, Tuple
import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from backend.app.models.dataset import DatasetMetadata
from backend.app.models.machine import Machine, MachineStatus, MachineType, SplitCategory
from backend.app.models.telemetry import TelemetryRecord


class MachineRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_machines(
        self,
        skip: int = 0,
        limit: int = 50,
        machine_type: Optional[MachineType] = None,
        status: Optional[MachineStatus] = None,
        split_category: Optional[SplitCategory] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Machine], int]:
        query = select(Machine)

        if machine_type:
            query = query.where(Machine.machine_type == machine_type)
        if status:
            query = query.where(Machine.status == status)
        if split_category:
            query = query.where(Machine.split_category == split_category)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Machine.machine_id.ilike(search_pattern),
                    Machine.name.ilike(search_pattern),
                    Machine.source_entity_id.ilike(search_pattern),
                )
            )

        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()

        items = list(
            self.db.execute(
                query.order_by(Machine.machine_id.asc()).offset(skip).limit(limit)
            ).scalars().all()
        )
        return items, total

    def get_by_id(self, id_val: uuid.UUID) -> Optional[Machine]:
        return self.db.execute(
            select(Machine).options(joinedload(Machine.dataset)).where(Machine.id == id_val)
        ).scalar_one_or_none()

    def get_by_machine_id(self, machine_id_str: str) -> Optional[Machine]:
        # Handle lookup by either UUID string or machine_id string (e.g. TURBOFAN-ENG-001)
        try:
            val_uuid = uuid.UUID(machine_id_str)
            return self.get_by_id(val_uuid)
        except ValueError:
            return self.db.execute(
                select(Machine)
                .options(joinedload(Machine.dataset))
                .where(Machine.machine_id == machine_id_str.strip())
            ).scalar_one_or_none()

    def get_telemetry_cycles(
        self,
        machine_id: uuid.UUID,
        start_cycle: Optional[int] = None,
        end_cycle: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[TelemetryRecord], int, int, int]:
        """Retrieve bounded, ordered telemetry cycles for an asset."""
        bounds = self.db.execute(
            select(
                func.min(TelemetryRecord.source_cycle),
                func.max(TelemetryRecord.source_cycle),
                func.count(TelemetryRecord.id),
            ).where(TelemetryRecord.machine_id == machine_id)
        ).one()

        min_avail = bounds[0] or 0
        max_avail = bounds[1] or 0
        total_records = bounds[2] or 0

        query = select(TelemetryRecord).where(TelemetryRecord.machine_id == machine_id)

        effective_start = start_cycle if start_cycle is not None else min_avail
        effective_end = end_cycle if end_cycle is not None else max_avail

        query = query.where(
            TelemetryRecord.source_cycle >= effective_start,
            TelemetryRecord.source_cycle <= effective_end,
        )

        records = list(
            self.db.execute(
                query.order_by(TelemetryRecord.source_cycle.asc())
                .offset(offset)
                .limit(limit)
            ).scalars().all()
        )

        return records, total_records, min_avail, max_avail

    def get_foundation_stats(self) -> dict:
        total_machines = self.db.execute(select(func.count(Machine.id))).scalar_one()
        total_telemetry = self.db.execute(select(func.count(TelemetryRecord.id))).scalar_one()
        operational_count = self.db.execute(
            select(func.count(Machine.id)).where(Machine.status == MachineStatus.OPERATIONAL)
        ).scalar_one()
        degraded_count = self.db.execute(
            select(func.count(Machine.id)).where(Machine.status == MachineStatus.DEGRADED)
        ).scalar_one()
        maintenance_count = self.db.execute(
            select(func.count(Machine.id)).where(Machine.status == MachineStatus.MAINTENANCE)
        ).scalar_one()
        datasets_registered = self.db.execute(select(func.count(DatasetMetadata.id))).scalar_one()

        return {
            "total_machines": total_machines,
            "total_telemetry_records": total_telemetry,
            "operational_count": operational_count,
            "degraded_count": degraded_count,
            "maintenance_count": maintenance_count,
            "datasets_registered": datasets_registered,
        }
