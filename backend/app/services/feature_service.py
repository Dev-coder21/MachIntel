from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.services.analytics_service import (
    ACTIVE_CHANNELS,
    ACTIVE_OP_SETTINGS,
    ACTIVE_SENSORS,
    INVARIANT_CHANNELS,
    MachineAnalyticsService,
    RollingFeatureCalculator,
)


@dataclass(frozen=True)
class FeatureEngineeringContract:
    """
    Formal interface and configuration contract for Milestone M4 (ML RUL Modeling).
    Enforces reproducible feature extraction, active sensor filtering, and strict temporal causality.
    """
    feature_engineering_version: str = "1.0.0"
    preprocessing_version: str = "1.0.0"
    window_size: int = 20
    min_periods: int = 1
    active_sensors: List[str] = field(default_factory=lambda: list(ACTIVE_SENSORS))
    active_op_settings: List[str] = field(default_factory=lambda: list(ACTIVE_OP_SETTINGS))
    invariant_channels: List[str] = field(default_factory=lambda: list(INVARIANT_CHANNELS))
    transformations: List[str] = field(
        default_factory=lambda: [
            "raw",
            "rolling_mean",
            "rolling_std",
            "rolling_min",
            "rolling_max",
            "rolling_slope",
        ]
    )
    scaling_policy: str = "FIT_ON_INTERNAL_TRAIN_ONLY"
    target_rul_piecewise_cap: int = 125  # Approved Phase 0 RUL clipping threshold


class FeatureExtractionService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics_service = MachineAnalyticsService(db)
        self.contract = FeatureEngineeringContract()

    def get_feature_names(self) -> List[str]:
        """Returns the deterministic list of all 96 derived feature column names."""
        names: List[str] = []
        for ch in ACTIVE_CHANNELS:
            names.append(f"{ch}_raw")
            names.append(f"{ch}_rolling_mean_w{self.contract.window_size}")
            names.append(f"{ch}_rolling_std_w{self.contract.window_size}")
            names.append(f"{ch}_rolling_min_w{self.contract.window_size}")
            names.append(f"{ch}_rolling_max_w{self.contract.window_size}")
            names.append(f"{ch}_rolling_slope_w{self.contract.window_size}")
        return names

    def extract_features_df(
        self,
        machine_id_str: str,
        start_cycle: Optional[int] = None,
        end_cycle: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Extracts the full feature matrix for a specific engine strictly obeying temporal causality.
        """
        machine = self.analytics_service._get_machine(machine_id_str)
        raw_df = self.analytics_service._load_telemetry_df(machine.id)

        if raw_df.empty:
            return pd.DataFrame(columns=["source_cycle"] + self.get_feature_names())

        cycles = raw_df["source_cycle"].to_numpy(dtype=int)
        feature_data: Dict[str, Any] = {"source_cycle": cycles}

        for ch in ACTIVE_CHANNELS:
            vals = raw_df[ch].to_numpy(dtype=float)
            r_mean, r_std, r_min, r_max, r_slope = RollingFeatureCalculator.calculate_rolling_features(
                cycles=cycles,
                values=vals,
                window=self.contract.window_size,
            )
            feature_data[f"{ch}_raw"] = vals
            feature_data[f"{ch}_rolling_mean_w{self.contract.window_size}"] = r_mean
            feature_data[f"{ch}_rolling_std_w{self.contract.window_size}"] = r_std
            feature_data[f"{ch}_rolling_min_w{self.contract.window_size}"] = r_min
            feature_data[f"{ch}_rolling_max_w{self.contract.window_size}"] = r_max
            feature_data[f"{ch}_rolling_slope_w{self.contract.window_size}"] = r_slope

        result_df = pd.DataFrame(feature_data)

        if start_cycle is not None:
            result_df = result_df[result_df["source_cycle"] >= start_cycle]
        if end_cycle is not None:
            result_df = result_df[result_df["source_cycle"] <= end_cycle]

        return result_df.reset_index(drop=True)

    def get_contract_metadata(self) -> Dict[str, Any]:
        """Provides metadata dictionary for model provenance and tracking."""
        return {
            "feature_engineering_version": self.contract.feature_engineering_version,
            "preprocessing_version": self.contract.preprocessing_version,
            "window_size": self.contract.window_size,
            "min_periods": self.contract.min_periods,
            "active_sensor_count": len(self.contract.active_sensors),
            "active_sensors": self.contract.active_sensors,
            "active_op_settings": self.contract.active_op_settings,
            "invariant_channels": self.contract.invariant_channels,
            "total_feature_count": len(self.get_feature_names()),
            "scaling_policy": self.contract.scaling_policy,
            "target_rul_piecewise_cap": self.contract.target_rul_piecewise_cap,
        }
