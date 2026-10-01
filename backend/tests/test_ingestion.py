import os
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.app.models.dataset import DatasetMetadata
from backend.app.models.machine import Machine, SplitCategory
from backend.app.models.telemetry import TelemetryRecord
from backend.app.services.ingestion_service import IngestionService

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/raw/cmapss/FD001"))


def test_ingestion_service_metadata_and_counts(db: Session):
    service = IngestionService(db)
    meta = db.execute(
        select(DatasetMetadata).where(DatasetMetadata.dataset_name == "NASA_CMAPSS_FD001")
    ).scalar_one_or_none()

    assert meta is not None
    assert meta.dataset_identifier == "FD001"
    assert len(meta.active_sensors) == 15
    assert len(meta.invariant_sensors) == 7

    # Machine count check
    train_count = db.execute(
        select(func.count(Machine.id)).where(Machine.split_category == SplitCategory.INTERNAL_TRAIN)
    ).scalar_one()
    assert train_count == 80

    val_count = db.execute(
        select(func.count(Machine.id)).where(Machine.split_category == SplitCategory.INTERNAL_VAL)
    ).scalar_one()
    assert val_count == 20

    test_count = db.execute(
        select(func.count(Machine.id)).where(Machine.split_category == SplitCategory.EVAL_TEST)
    ).scalar_one()
    assert test_count == 100

    # Total telemetry count
    total_telemetry = db.execute(select(func.count(TelemetryRecord.id))).scalar_one()
    assert total_telemetry == 33727


def test_ingestion_service_idempotency(db: Session):
    service = IngestionService(db)
    # Run ingestion again on the active database
    result = service.ingest_cmapss_fd001(DATA_DIR)

    assert result["total_telemetry_rows"] == 33727
    # Telemetry count must remain unchanged
    total_telemetry = db.execute(select(func.count(TelemetryRecord.id))).scalar_one()
    assert total_telemetry == 33727
