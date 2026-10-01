import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.models.dataset import DatasetMetadata
from backend.app.models.machine import Machine, MachineStatus, MachineType, SplitCategory
from backend.app.models.telemetry import TelemetryRecord
from backend.app.models.data_quality import DataQualityIssue


COLUMNS = [
    "unit_number",
    "time_in_cycles",
    "op_setting_1",
    "op_setting_2",
    "op_setting_3",
] + [f"sensor_{i}" for i in range(1, 22)]

INVARIANT_CHANNELS_FD001 = [
    "op_setting_3",
    "sensor_1",
    "sensor_5",
    "sensor_10",
    "sensor_16",
    "sensor_18",
    "sensor_19",
]

ACTIVE_CHANNELS_FD001 = [
    f"sensor_{i}"
    for i in range(1, 22)
    if f"sensor_{i}" not in INVARIANT_CHANNELS_FD001
]


class IngestionService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def compute_sha256(filepath: str) -> str:
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def parse_raw_file(self, filepath: str) -> Tuple[np.ndarray, int]:
        """Parse space-delimited C-MAPSS text file into 2D float array."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Raw C-MAPSS file not found at: {filepath}")

        rows = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                parts = stripped.split()
                if len(parts) < 26:
                    raise ValueError(
                        f"Malformed row at line {line_idx} in {filepath}: expected 26 columns, found {len(parts)}"
                    )
                try:
                    # Parse first 26 columns
                    row_vals = [float(x) for x in parts[:26]]
                    rows.append(row_vals)
                except ValueError as exc:
                    raise ValueError(f"Non-numeric value at line {line_idx} in {filepath}: {exc}")

        data_array = np.array(rows, dtype=np.float64)
        return data_array, len(rows)

    def parse_rul_file(self, filepath: str) -> List[int]:
        """Parse ground truth RUL vector file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"RUL vector file not found at: {filepath}")

        ruls = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                val = line.strip()
                if not val:
                    continue
                try:
                    ruls.append(int(float(val)))
                except ValueError as exc:
                    raise ValueError(f"Malformed RUL at line {line_idx} in {filepath}: {exc}")
        return ruls

    def validate_data_quality(
        self,
        data_array: np.ndarray,
        split_name: str,
        dataset_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """Run empirical data quality checks across parsed matrix."""
        issues = []
        units = np.unique(data_array[:, 0].astype(int))

        # Check for NaN / Inf
        if np.isnan(data_array).any() or np.isinf(data_array).any():
            issues.append({
                "field_name": "all_sensors",
                "issue_type": "NULL_OR_INF_VALUE",
                "severity": "CRITICAL",
                "description": f"Found NaN or Infinite values in {split_name} matrix",
            })

        # Check cycle monotonicity and continuity per unit
        for unit in units:
            unit_mask = data_array[:, 0] == unit
            unit_cycles = data_array[unit_mask, 1].astype(int)

            # Check duplicates
            if len(unit_cycles) != len(np.unique(unit_cycles)):
                issues.append({
                    "field_name": "time_in_cycles",
                    "issue_type": "DUPLICATE_CYCLE",
                    "severity": "CRITICAL",
                    "description": f"Engine Unit {unit} has duplicate operational cycles in {split_name}",
                })

            # Check strict monotonic increment
            diffs = np.diff(unit_cycles)
            if not (diffs == 1).all():
                issues.append({
                    "field_name": "time_in_cycles",
                    "issue_type": "NON_MONOTONIC_OR_GAP",
                    "severity": "CRITICAL",
                    "description": f"Engine Unit {unit} has non-sequential cycles in {split_name}",
                })

        # Check standard deviations for invariant channels
        for col_idx in range(2, 26):
            col_name = COLUMNS[col_idx]
            std_val = float(np.std(data_array[:, col_idx]))
            if std_val < 1e-6:
                issues.append({
                    "field_name": col_name,
                    "issue_type": "INVARIANT_CHANNEL",
                    "severity": "INFO",
                    "description": f"Sensor channel '{col_name}' has 0.0 standard deviation in {split_name} (constant channel)",
                })

        return issues

    def ingest_cmapss_fd001(self, raw_dir: str) -> Dict[str, Any]:
        """
        Execute full idempotent ingestion of NASA C-MAPSS FD001.
        Preserves raw data, creates metadata provenance, registers machines,
        and bulk-loads telemetry cycles.
        """
        train_file = os.path.join(raw_dir, "train_FD001.txt")
        test_file = os.path.join(raw_dir, "test_FD001.txt")
        rul_file = os.path.join(raw_dir, "RUL_FD001.txt")

        logger.info(f"Starting ingestion from directory: {raw_dir}")

        # 1. Parse and validate raw text files
        train_data, train_lines = self.parse_raw_file(train_file)
        test_data, test_lines = self.parse_raw_file(test_file)
        rul_values = self.parse_rul_file(rul_file)

        if len(rul_values) != 100:
            raise ValueError(f"Expected exactly 100 RUL ground truth values, got {len(rul_values)}")

        # 2. Compute file checksums
        file_checksums = {
            "train_FD001.txt": {
                "sha256": self.compute_sha256(train_file),
                "lines": train_lines,
                "bytes": os.path.getsize(train_file),
            },
            "test_FD001.txt": {
                "sha256": self.compute_sha256(test_file),
                "lines": test_lines,
                "bytes": os.path.getsize(test_file),
            },
            "RUL_FD001.txt": {
                "sha256": self.compute_sha256(rul_file),
                "lines": len(rul_values),
                "bytes": os.path.getsize(rul_file),
            },
        }

        # 3. Create or update DatasetMetadata record
        dataset_meta = self.db.execute(
            select(DatasetMetadata).where(DatasetMetadata.dataset_name == "NASA_CMAPSS_FD001")
        ).scalar_one_or_none()

        if not dataset_meta:
            dataset_meta = DatasetMetadata(
                dataset_name="NASA_CMAPSS_FD001",
                dataset_identifier="FD001",
                source="NASA Prognostics Center of Excellence (PCoE) Data Repository",
                source_url="https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/",
                license="Public Domain / NASA Open Data Policy",
                retrieval_date=datetime.now(timezone.utc),
                file_checksums=file_checksums,
                schema_version="1.0.0",
                preprocessing_version="1.0.0",
                ingestion_version="1.0.0",
                active_sensors=ACTIVE_CHANNELS_FD001,
                invariant_sensors=INVARIANT_CHANNELS_FD001,
            )
            self.db.add(dataset_meta)
            self.db.commit()
            self.db.refresh(dataset_meta)
            logger.info(f"Created DatasetMetadata ID: {dataset_meta.id}")
        else:
            dataset_meta.file_checksums = file_checksums
            dataset_meta.active_sensors = ACTIVE_CHANNELS_FD001
            dataset_meta.invariant_sensors = INVARIANT_CHANNELS_FD001
            self.db.commit()
            self.db.refresh(dataset_meta)

        # 4. Data Quality Audit & Persistence
        self.db.execute(
            delete(DataQualityIssue).where(DataQualityIssue.dataset_id == dataset_meta.id)
        )
        train_issues = self.validate_data_quality(train_data, "train_FD001", dataset_meta.id)
        for issue in train_issues:
            self.db.add(
                DataQualityIssue(
                    dataset_id=dataset_meta.id,
                    field_name=issue["field_name"],
                    issue_type=issue["issue_type"],
                    severity=issue["severity"],
                    description=issue["description"],
                )
            )
        self.db.commit()

        batch_id = uuid.uuid4()
        machines_created = 0
        telemetry_rows_inserted = 0

        # 5. Ingest Training Engines (Units 1 to 100)
        train_units = np.unique(train_data[:, 0].astype(int))
        for unit in train_units:
            machine_id = f"TURBOFAN-ENG-{unit:03d}"
            split_category = (
                SplitCategory.INTERNAL_TRAIN if unit <= 80 else SplitCategory.INTERNAL_VAL
            )

            unit_mask = train_data[:, 0] == unit
            unit_slice = train_data[unit_mask]
            total_cycles = int(len(unit_slice))
            max_cycle = int(np.max(unit_slice[:, 1]))

            machine = self.db.execute(
                select(Machine).where(Machine.machine_id == machine_id)
            ).scalar_one_or_none()

            if not machine:
                machine = Machine(
                    machine_id=machine_id,
                    name=f"Turbofan High-Bypass Engine #{unit:03d}",
                    machine_type=MachineType.TURBOFAN_ENGINE,
                    source_dataset="NASA_CMAPSS_FD001",
                    source_entity_id=str(unit),
                    dataset_id=dataset_meta.id,
                    status=MachineStatus.OPERATIONAL,
                    split_category=split_category,
                    total_cycles=total_cycles,
                    max_cycle=max_cycle,
                    ground_truth_rul=0,  # Run-to-failure endpoint has 0 cycles remaining at max_cycle
                    metadata_json={
                        "condition": "Sea-Level (Nominal)",
                        "failure_mode": "HPC Degradation",
                        "split": "TRAIN",
                    },
                )
                self.db.add(machine)
                self.db.commit()
                self.db.refresh(machine)
                machines_created += 1
            else:
                machine.total_cycles = total_cycles
                machine.max_cycle = max_cycle
                self.db.commit()

            # Insert telemetry rows in chunks
            telemetry_records = []
            for row in unit_slice:
                telemetry_records.append({
                    "id": uuid.uuid4(),
                    "machine_id": machine.id,
                    "source_cycle": int(row[1]),
                    "event_timestamp": None,  # Preserving cycle abstraction without fake timestamps
                    "split_type": "TRAIN",
                    "op_setting_1": float(row[2]),
                    "op_setting_2": float(row[3]),
                    "op_setting_3": float(row[4]),
                    "sensor_1": float(row[5]),
                    "sensor_2": float(row[6]),
                    "sensor_3": float(row[7]),
                    "sensor_4": float(row[8]),
                    "sensor_5": float(row[9]),
                    "sensor_6": float(row[10]),
                    "sensor_7": float(row[11]),
                    "sensor_8": float(row[12]),
                    "sensor_9": float(row[13]),
                    "sensor_10": float(row[14]),
                    "sensor_11": float(row[15]),
                    "sensor_12": float(row[16]),
                    "sensor_13": float(row[17]),
                    "sensor_14": float(row[18]),
                    "sensor_15": float(row[19]),
                    "sensor_16": float(row[20]),
                    "sensor_17": float(row[21]),
                    "sensor_18": float(row[22]),
                    "sensor_19": float(row[23]),
                    "sensor_20": float(row[24]),
                    "sensor_21": float(row[25]),
                    "ingestion_batch_id": batch_id,
                    "created_at": datetime.now(timezone.utc),
                })

            # Idempotent bulk upsert / insert
            stmt = insert(TelemetryRecord).values(telemetry_records)
            stmt = stmt.on_conflict_do_nothing(
                constraint="uq_telemetry_machine_cycle_split"
            )
            result = self.db.execute(stmt)
            self.db.commit()
            if result.rowcount > 0:
                telemetry_rows_inserted += result.rowcount

        # 6. Ingest Censored Evaluation Test Engines (Units 1 to 100)
        test_units = np.unique(test_data[:, 0].astype(int))
        for unit in test_units:
            machine_id = f"TURBOFAN-ENG-TEST-{unit:03d}"
            unit_mask = test_data[:, 0] == unit
            unit_slice = test_data[unit_mask]
            total_cycles = int(len(unit_slice))
            max_cycle = int(np.max(unit_slice[:, 1]))
            true_rul = rul_values[unit - 1]

            machine = self.db.execute(
                select(Machine).where(Machine.machine_id == machine_id)
            ).scalar_one_or_none()

            if not machine:
                machine = Machine(
                    machine_id=machine_id,
                    name=f"Turbofan Evaluation Test Engine #{unit:03d}",
                    machine_type=MachineType.TURBOFAN_ENGINE,
                    source_dataset="NASA_CMAPSS_FD001",
                    source_entity_id=str(unit),
                    dataset_id=dataset_meta.id,
                    status=MachineStatus.OPERATIONAL,
                    split_category=SplitCategory.EVAL_TEST,
                    total_cycles=total_cycles,
                    max_cycle=max_cycle,
                    ground_truth_rul=true_rul,
                    metadata_json={
                        "condition": "Sea-Level (Nominal)",
                        "failure_mode": "HPC Degradation",
                        "split": "TEST",
                        "censored_at_cycle": max_cycle,
                        "ground_truth_remaining_useful_life": true_rul,
                    },
                )
                self.db.add(machine)
                self.db.commit()
                self.db.refresh(machine)
                machines_created += 1
            else:
                machine.total_cycles = total_cycles
                machine.max_cycle = max_cycle
                machine.ground_truth_rul = true_rul
                self.db.commit()

            telemetry_records = []
            for row in unit_slice:
                telemetry_records.append({
                    "id": uuid.uuid4(),
                    "machine_id": machine.id,
                    "source_cycle": int(row[1]),
                    "event_timestamp": None,
                    "split_type": "TEST",
                    "op_setting_1": float(row[2]),
                    "op_setting_2": float(row[3]),
                    "op_setting_3": float(row[4]),
                    "sensor_1": float(row[5]),
                    "sensor_2": float(row[6]),
                    "sensor_3": float(row[7]),
                    "sensor_4": float(row[8]),
                    "sensor_5": float(row[9]),
                    "sensor_6": float(row[10]),
                    "sensor_7": float(row[11]),
                    "sensor_8": float(row[12]),
                    "sensor_9": float(row[13]),
                    "sensor_10": float(row[14]),
                    "sensor_11": float(row[15]),
                    "sensor_12": float(row[16]),
                    "sensor_13": float(row[17]),
                    "sensor_14": float(row[18]),
                    "sensor_15": float(row[19]),
                    "sensor_16": float(row[20]),
                    "sensor_17": float(row[21]),
                    "sensor_18": float(row[22]),
                    "sensor_19": float(row[23]),
                    "sensor_20": float(row[24]),
                    "sensor_21": float(row[25]),
                    "ingestion_batch_id": batch_id,
                    "created_at": datetime.now(timezone.utc),
                })

            stmt = insert(TelemetryRecord).values(telemetry_records)
            stmt = stmt.on_conflict_do_nothing(
                constraint="uq_telemetry_machine_cycle_split"
            )
            result = self.db.execute(stmt)
            self.db.commit()
            if result.rowcount > 0:
                telemetry_rows_inserted += result.rowcount

        logger.info(
            f"Ingestion complete: {machines_created} machines registered, "
            f"{telemetry_rows_inserted} telemetry records inserted."
        )

        return {
            "dataset": "NASA_CMAPSS_FD001",
            "ingestion_batch_id": str(batch_id),
            "machines_registered": len(train_units) + len(test_units),
            "train_engines": len(train_units),
            "test_engines": len(test_units),
            "train_telemetry_rows": train_lines,
            "test_telemetry_rows": test_lines,
            "total_telemetry_rows": train_lines + test_lines,
            "telemetry_rows_inserted": telemetry_rows_inserted,
            "data_quality_issues_detected": len(train_issues),
        }
