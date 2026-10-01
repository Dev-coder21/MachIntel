import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid
import joblib
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select, or_
from sqlalchemy.orm import Session

from backend.app.models.dataset import DatasetMetadata
from backend.app.models.machine import Machine
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.prediction import OperationalState, Prediction
from backend.app.services.feature_service import FeatureExtractionService


# In-memory artifact cache to avoid loading from disk on every prediction
_MODEL_CACHE: Dict[str, Tuple[Any, Any, List[str]]] = {}


def derive_operational_state(health_index: float) -> OperationalState:
    """
    Approved deterministic interpretation thresholds:
    HI >= 0.70 -> NORMAL
    0.40 <= HI < 0.70 -> WATCH
    0.15 <= HI < 0.40 -> ELEVATED
    HI < 0.15 -> CRITICAL
    """
    if health_index >= 0.70:
        return OperationalState.NORMAL
    elif health_index >= 0.40:
        return OperationalState.WATCH
    elif health_index >= 0.15:
        return OperationalState.ELEVATED
    else:
        return OperationalState.CRITICAL


class PredictionService:
    def __init__(self, db: Session):
        self.db = db
        self.feature_service = FeatureExtractionService(db)

    def _get_model(self, model_id: Optional[str] = None) -> ModelRegistry:
        """Resolves the requested model or the active production model from the registry."""
        from backend.app.services.model_lifecycle_service import ModelLifecycleService
        from backend.app.models.model_registry import ModelDomain

        if model_id:
            stmt = select(ModelRegistry).where(ModelRegistry.model_id == model_id)
            model_reg = self.db.execute(stmt).scalar_one_or_none()
            if not model_reg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model '{model_id}' not found in registry.",
                )
        else:
            model_reg = ModelLifecycleService.get_active_model(self.db, domain=ModelDomain.MACHINE_HEALTH.value)

        return model_reg

    def _load_artifacts(self, model_reg: ModelRegistry) -> Tuple[Any, Any, List[str]]:
        """Loads model, scaler, and feature names, utilizing in-memory caching and verifying integrity."""
        if model_reg.model_id in _MODEL_CACHE:
            return _MODEL_CACHE[model_reg.model_id]

        from backend.app.services.model_lifecycle_service import ModelLifecycleService, safe_resolve_artifact_path

        base_dir = safe_resolve_artifact_path(model_reg.artifact_path)

        # Enforce artifact cryptographic integrity check
        integrity = ModelLifecycleService.verify_artifact_integrity(model_reg)
        if not integrity["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Model artifact '{model_reg.model_id}' failed SHA-256 integrity verification. Refusing to serve compromised artifact.",
            )

        model_path = base_dir / "model.joblib"
        scaler_path = base_dir / "scaler.joblib"

        if not model_path.exists() or not scaler_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Model artifact files not found at {model_reg.artifact_path}",
            )

        model_obj = joblib.load(model_path)
        scaler_obj = joblib.load(scaler_path)
        feat_names = model_reg.feature_names or self.feature_service.get_feature_names()

        _MODEL_CACHE[model_reg.model_id] = (model_obj, scaler_obj, feat_names)
        return model_obj, scaler_obj, feat_names

    def _get_machine(self, machine_identifier: str) -> Machine:
        """Resolves Machine by machine_id string (e.g. 'FD001-001') or UUID."""
        machine = None
        try:
            val_uuid = uuid.UUID(machine_identifier)
            machine = self.db.execute(
                select(Machine).where(
                    (Machine.machine_id == machine_identifier) | (Machine.id == val_uuid)
                )
            ).scalar_one_or_none()
        except (ValueError, AttributeError):
            machine = self.db.execute(
                select(Machine).where(Machine.machine_id == machine_identifier)
            ).scalar_one_or_none()

        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_identifier}' not found.",
            )
        return machine

    def predict_machine_health(
        self,
        machine_identifier: str,
        observation_cycle: Optional[int] = None,
        model_version: Optional[str] = None,
        persist: bool = True,
    ) -> Prediction:
        """
        Executes end-to-end RUL regression and derived health state for a given machine and cycle.
        """
        # 1. Resolve machine
        machine = self._get_machine(machine_identifier)

        # 2. Resolve target cycle
        if observation_cycle is None:
            observation_cycle = machine.max_cycle
        elif observation_cycle < 1 or observation_cycle > machine.max_cycle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Observation cycle {observation_cycle} is out of bounds for machine {machine.machine_id} (valid range: 1 to {machine.max_cycle}).",
            )

        # 3. Load model & scaler
        model_reg = self._get_model(model_version)
        model_obj, scaler_obj, feature_names = self._load_artifacts(model_reg)

        # 4. Extract causal features strictly up to observation_cycle
        feat_df = self.feature_service.extract_features_df(
            machine_id_str=machine.machine_id,
            end_cycle=observation_cycle,
        )

        if feat_df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No telemetry available for machine {machine.machine_id} up to cycle {observation_cycle}.",
            )

        # Vector at observation_cycle
        obs_row = feat_df[feat_df["source_cycle"] == observation_cycle]
        if obs_row.empty:
            obs_row = feat_df.iloc[[-1]]

        feature_vector = obs_row[feature_names].to_numpy(dtype=float)

        # 5. Apply scaler and inference
        feature_scaled = scaler_obj.transform(feature_vector)
        raw_rul = float(model_obj.predict(feature_scaled)[0])

        # 6. Physical bounds clamping and Health Index calculation
        clamped_rul = max(0.0, raw_rul)
        health_index = min(1.0, max(0.0, clamped_rul / 125.0))
        op_state = derive_operational_state(health_index)

        # Dataset provenance
        dataset_meta = self.db.execute(
            select(DatasetMetadata).where(DatasetMetadata.dataset_name == "NASA-C-MAPSS-FD001")
        ).scalar_one_or_none()

        # 7. Create Prediction record
        prediction = Prediction(
            machine_id=machine.id,
            model_version_id=model_reg.id,
            dataset_id=dataset_meta.id if dataset_meta else None,
            feature_engineering_version=model_reg.feature_engineering_version,
            observation_cycle=observation_cycle,
            predicted_rul=round(clamped_rul, 2),
            health_index=round(health_index, 4),
            operational_state=op_state.value,
            metadata_json={
                "algorithm": model_reg.algorithm,
                "raw_predicted_rul": round(raw_rul, 4),
                "capped_at_cycle": observation_cycle,
                "feature_count": len(feature_names),
                "disclaimer": "Analytical risk interpretation derived from baseline statistical regression; not a certified safety determination.",
            },
        )

        if persist:
            self.db.add(prediction)
            self.db.commit()
            self.db.refresh(prediction)

            # M5: Deterministic risk assessment and alert generation
            from backend.app.services.risk_engine import RiskEngine
            from backend.app.services.alert_service import AlertService
            risk_engine = RiskEngine(self.db)
            assessment = risk_engine.evaluate_prediction(prediction, machine, persist=True)
            alert_svc = AlertService(self.db)
            alert_svc.process_risk_assessment(assessment, machine)

        return prediction

    def get_latest_prediction(self, machine_identifier: str) -> Optional[Prediction]:
        """Returns the most recent persisted prediction for an engine."""
        machine = self._get_machine(machine_identifier)

        stmt = (
            select(Prediction)
            .where(Prediction.machine_id == machine.id)
            .order_by(Prediction.observation_cycle.desc(), Prediction.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_prediction_history(
        self,
        machine_identifier: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Prediction], int]:
        """Returns paginated prediction history for an engine."""
        machine = self._get_machine(machine_identifier)

        base_stmt = select(Prediction).where(Prediction.machine_id == machine.id)
        total = self.db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0

        stmt = (
            base_stmt
            .order_by(Prediction.observation_cycle.desc(), Prediction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def get_fleet_overview(self) -> Dict[str, Any]:
        """Aggregates latest fleet-wide prognostic metrics for Dashboard."""
        active_model = self.db.execute(
            select(ModelRegistry).where(
                ModelRegistry.is_active == True,
                or_(ModelRegistry.domain == "MACHINE_HEALTH", ModelRegistry.domain.is_(None)),
            )
        ).scalars().first()

        total_machines = self.db.scalar(select(func.count(Machine.id))) or 0

        # Subquery for latest prediction per machine
        subquery = (
            select(
                Prediction.machine_id,
                func.max(Prediction.observation_cycle).label("max_cycle")
            )
            .group_by(Prediction.machine_id)
            .subquery()
        )

        latest_preds_stmt = (
            select(Prediction)
            .join(
                subquery,
                (Prediction.machine_id == subquery.c.machine_id) &
                (Prediction.observation_cycle == subquery.c.max_cycle)
            )
        )
        latest_preds = list(self.db.execute(latest_preds_stmt).scalars().all())

        state_dist = {"NORMAL": 0, "WATCH": 0, "ELEVATED": 0, "CRITICAL": 0}
        rul_sum = 0.0
        hi_sum = 0.0

        for p in latest_preds:
            st = p.operational_state
            if st in state_dist:
                state_dist[st] += 1
            rul_sum += p.predicted_rul
            hi_sum += p.health_index

        n = len(latest_preds)
        avg_rul = round(rul_sum / n, 2) if n > 0 else None
        avg_hi = round(hi_sum / n, 4) if n > 0 else None

        return {
            "total_machines": total_machines,
            "machines_with_predictions": n,
            "active_model_id": active_model.model_id if active_model else "none",
            "active_model_algorithm": active_model.algorithm if active_model else "none",
            "average_predicted_rul": avg_rul,
            "average_health_index": avg_hi,
            "state_distribution": state_dist,
        }
