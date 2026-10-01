import math
from typing import Dict, List, Optional, Tuple
import uuid
import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundException, ValidationException
from backend.app.models.machine import Machine, SplitCategory
from backend.app.models.telemetry import TelemetryRecord
from backend.app.schemas.analytics import (
    CorrelationMatrixResponse,
    FeatureColumnMeta,
    FeaturePreviewResponse,
    FeaturePreviewRow,
    FleetAnalyticsOverviewResponse,
    MachineAnalyticsSummary,
    MachineComparisonItem,
    MachineComparisonResponse,
    SensorSummaryItem,
    SensorTrendResponse,
    TrendPoint,
)

CHANNEL_METADATA: Dict[str, Dict[str, str]] = {
    "op_setting_1": {"name": "Mach Number", "unit": "Mach", "desc": "Flight condition Mach number"},
    "op_setting_2": {"name": "Throttle Resolver Angle", "unit": "TRA", "desc": "Power lever angle setting"},
    "sensor_2": {"name": "Total Temperature at LPC Outlet", "unit": "°R", "desc": "LPC outlet temperature (T24)"},
    "sensor_3": {"name": "Total Temperature at HPC Outlet", "unit": "°R", "desc": "HPC outlet temperature (T30)"},
    "sensor_4": {"name": "Total Temperature at LPT Outlet", "unit": "°R", "desc": "LPT outlet temperature (T50)"},
    "sensor_6": {"name": "Total Pressure in Bypass Duct", "unit": "psia", "desc": "Bypass duct pressure (P2)"},
    "sensor_7": {"name": "Total Pressure at HPC Outlet", "unit": "psia", "desc": "HPC outlet total pressure (P30)"},
    "sensor_8": {"name": "Physical Fan Speed", "unit": "rpm", "desc": "Fan rotational speed (Nf)"},
    "sensor_9": {"name": "Physical Core Speed", "unit": "rpm", "desc": "Core rotational speed (Nc)"},
    "sensor_11": {"name": "Static Pressure at HPC Outlet", "unit": "psia", "desc": "HPC outlet static pressure (Ps30)"},
    "sensor_12": {"name": "Ratio of Fuel Flow to Ps30", "unit": "pps/psi", "desc": "Fuel-air flow ratio (phi)"},
    "sensor_13": {"name": "Corrected Fan Speed", "unit": "rpm", "desc": "Corrected fan speed (NRf)"},
    "sensor_14": {"name": "Corrected Core Speed", "unit": "rpm", "desc": "Corrected core speed (NRc)"},
    "sensor_15": {"name": "Bypass Ratio", "unit": "—", "desc": "Bypass air mass ratio (BPR)"},
    "sensor_17": {"name": "Bleed Enthalpy", "unit": "—", "desc": "Enthalpy of bleed air (htBleed)"},
    "sensor_20": {"name": "HPT Coolant Bleed", "unit": "lbm/s", "desc": "HPT coolant flow rate (W31)"},
    "sensor_21": {"name": "LPT Coolant Bleed", "unit": "lbm/s", "desc": "LPT coolant flow rate (W32)"},
}

ACTIVE_SENSORS = [
    "sensor_2",
    "sensor_3",
    "sensor_4",
    "sensor_6",
    "sensor_7",
    "sensor_8",
    "sensor_9",
    "sensor_11",
    "sensor_12",
    "sensor_13",
    "sensor_14",
    "sensor_15",
    "sensor_17",
    "sensor_20",
    "sensor_21",
]

ACTIVE_OP_SETTINGS = ["op_setting_1", "op_setting_2"]

ACTIVE_CHANNELS = ACTIVE_OP_SETTINGS + ACTIVE_SENSORS

INVARIANT_CHANNELS = [
    "op_setting_3",
    "sensor_1",
    "sensor_5",
    "sensor_10",
    "sensor_16",
    "sensor_18",
    "sensor_19",
]


class RollingFeatureCalculator:
    """
    Computes temporally causal rolling features over a single machine's telemetry series.
    Guarantees:
    1. Zero lookahead: observation at cycle t only uses data from cycles <= t.
    2. Zero cross-machine leakage: executes strictly within machine isolation.
    3. Handles initial cycles (t < W) via expanding windows (min_periods=1).
    """

    @staticmethod
    def calculate_rolling_features(
        cycles: np.ndarray,
        values: np.ndarray,
        window: int = 20,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns:
            (rolling_mean, rolling_std, rolling_min, rolling_max, rolling_slope)
        """
        n = len(values)
        if n == 0:
            empty = np.array([], dtype=float)
            return empty, empty, empty, empty, empty

        s = pd.Series(values)
        r = s.rolling(window=window, min_periods=1)

        r_mean = r.mean().to_numpy()
        r_std = r.std(ddof=1).fillna(0.0).to_numpy()
        r_min = r.min().to_numpy()
        r_max = r.max().to_numpy()

        # Rolling slope via Ordinary Least Squares over the causal trailing window
        r_slope = np.zeros(n, dtype=float)
        for i in range(n):
            start_idx = max(0, i - window + 1)
            k = i - start_idx + 1
            if k <= 1:
                r_slope[i] = 0.0
            else:
                x_win = cycles[start_idx : i + 1].astype(float)
                y_win = values[start_idx : i + 1].astype(float)
                x_mean = np.mean(x_win)
                y_mean = np.mean(y_win)
                denom = np.sum((x_win - x_mean) ** 2)
                if denom > 1e-12:
                    r_slope[i] = np.sum((x_win - x_mean) * (y_win - y_mean)) / denom
                else:
                    r_slope[i] = 0.0

        return r_mean, r_std, r_min, r_max, r_slope


class MachineAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _get_machine(self, machine_id_str: str) -> Machine:
        try:
            val_uuid = uuid.UUID(machine_id_str)
            m = self.db.execute(select(Machine).where(Machine.id == val_uuid)).scalar_one_or_none()
        except ValueError:
            m = self.db.execute(
                select(Machine).where(Machine.machine_id == machine_id_str.strip())
            ).scalar_one_or_none()

        if not m:
            raise NotFoundException(f"Machine '{machine_id_str}' was not found in the machine registry")
        return m

    def _load_telemetry_df(self, machine_uuid: uuid.UUID) -> pd.DataFrame:
        stmt = (
            select(
                TelemetryRecord.source_cycle,
                TelemetryRecord.op_setting_1,
                TelemetryRecord.op_setting_2,
                TelemetryRecord.sensor_2,
                TelemetryRecord.sensor_3,
                TelemetryRecord.sensor_4,
                TelemetryRecord.sensor_6,
                TelemetryRecord.sensor_7,
                TelemetryRecord.sensor_8,
                TelemetryRecord.sensor_9,
                TelemetryRecord.sensor_11,
                TelemetryRecord.sensor_12,
                TelemetryRecord.sensor_13,
                TelemetryRecord.sensor_14,
                TelemetryRecord.sensor_15,
                TelemetryRecord.sensor_17,
                TelemetryRecord.sensor_20,
                TelemetryRecord.sensor_21,
            )
            .where(TelemetryRecord.machine_id == machine_uuid)
            .order_by(TelemetryRecord.source_cycle.asc())
        )
        rows = self.db.execute(stmt).all()
        if not rows:
            return pd.DataFrame(columns=["source_cycle"] + ACTIVE_CHANNELS)

        df = pd.DataFrame(rows)
        return df

    def get_summary(self, machine_id_str: str) -> MachineAnalyticsSummary:
        machine = self._get_machine(machine_id_str)
        df = self._load_telemetry_df(machine.id)

        first_c = int(df["source_cycle"].min()) if not df.empty else 0
        latest_c = int(df["source_cycle"].max()) if not df.empty else 0
        total_c = len(df)

        sensor_items: List[SensorSummaryItem] = []
        for ch in ACTIVE_CHANNELS:
            meta = CHANNEL_METADATA.get(ch, {"name": ch, "unit": ""})
            if df.empty:
                sensor_items.append(
                    SensorSummaryItem(
                        sensor_key=ch,
                        channel_name=meta["name"],
                        engineering_unit=meta["unit"],
                        min_value=0.0,
                        max_value=0.0,
                        mean_value=0.0,
                        std_value=0.0,
                        initial_value=0.0,
                        latest_value=0.0,
                        net_change=0.0,
                        pct_change=0.0,
                        direction="STABLE",
                    )
                )
                continue

            vals = df[ch].to_numpy(dtype=float)
            min_v = float(np.min(vals))
            max_v = float(np.max(vals))
            mean_v = float(np.mean(vals))
            std_v = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            first_v = float(vals[0])
            last_v = float(vals[-1])
            net_chg = last_v - first_v

            pct_chg = None
            if abs(first_v) > 1e-6:
                pct_chg = float((net_chg / abs(first_v)) * 100.0)

            # Directional threshold: > 0.5% or > 0.01 net
            if pct_chg is not None and pct_chg > 0.5:
                direction = "INCREASING"
            elif pct_chg is not None and pct_chg < -0.5:
                direction = "DECREASING"
            else:
                direction = "STABLE"

            sensor_items.append(
                SensorSummaryItem(
                    sensor_key=ch,
                    channel_name=meta["name"],
                    engineering_unit=meta["unit"],
                    min_value=round(min_v, 4),
                    max_value=round(max_v, 4),
                    mean_value=round(mean_v, 4),
                    std_value=round(std_v, 4),
                    initial_value=round(first_v, 4),
                    latest_value=round(last_v, 4),
                    net_change=round(net_chg, 4),
                    pct_change=round(pct_chg, 2) if pct_chg is not None else None,
                    direction=direction,
                )
            )

        # Sort top drifting sensors by absolute percentage change (or net change if pct unavailable)
        top_drifting = sorted(
            sensor_items,
            key=lambda item: abs(item.pct_change) if item.pct_change is not None else abs(item.net_change),
            reverse=True,
        )[:5]

        return MachineAnalyticsSummary(
            machine_id=machine.machine_id,
            machine_name=machine.name,
            source_dataset=machine.source_dataset,
            source_entity_id=machine.source_entity_id,
            split_category=machine.split_category.value if hasattr(machine.split_category, "value") else str(machine.split_category),
            status=machine.status.value if hasattr(machine.status, "value") else str(machine.status),
            first_cycle=first_c,
            latest_cycle=latest_c,
            total_cycles=total_c,
            active_sensor_count=len(ACTIVE_SENSORS),
            invariant_sensor_count=len(INVARIANT_CHANNELS),
            top_drifting_sensors=top_drifting,
            sensors=sensor_items,
        )

    def get_sensors(self, machine_id_str: str) -> List[SensorSummaryItem]:
        summary = self.get_summary(machine_id_str)
        return summary.sensors

    def get_trends(
        self,
        machine_id_str: str,
        sensor: str,
        window: int = 20,
        max_points: int = 300,
    ) -> SensorTrendResponse:
        clean_sensor = sensor.strip().lower()

        if clean_sensor in INVARIANT_CHANNELS:
            raise ValidationException(
                f"Channel '{sensor}' is invariant (variance=0) in FD001 and is excluded from dynamic trend analytics."
            )

        if clean_sensor not in ACTIVE_CHANNELS:
            raise ValidationException(
                f"Channel '{sensor}' is not an active C-MAPSS channel. Supported active channels: {ACTIVE_CHANNELS}"
            )

        if window < 2 or window > 100:
            raise ValidationException("Window size must be between 2 and 100 cycles.")

        machine = self._get_machine(machine_id_str)
        df = self._load_telemetry_df(machine.id)

        meta = CHANNEL_METADATA.get(clean_sensor, {"name": clean_sensor, "unit": ""})
        total_cycles = len(df)

        if df.empty:
            return SensorTrendResponse(
                machine_id=machine.machine_id,
                sensor_key=clean_sensor,
                channel_name=meta["name"],
                engineering_unit=meta["unit"],
                window_size=window,
                total_cycles=0,
                returned_points=0,
                is_downsampled=False,
                direction="STABLE",
                overall_slope=0.0,
                points=[],
            )

        cycles = df["source_cycle"].to_numpy(dtype=int)
        raw_vals = df[clean_sensor].to_numpy(dtype=float)

        r_mean, r_std, r_min, r_max, r_slope = RollingFeatureCalculator.calculate_rolling_features(
            cycles=cycles,
            values=raw_vals,
            window=window,
        )

        overall_slope = float(r_slope[-1]) if len(r_slope) > 0 else 0.0
        net_chg = raw_vals[-1] - raw_vals[0]
        direction = "INCREASING" if net_chg > 0.01 else "DECREASING" if net_chg < -0.01 else "STABLE"

        all_points: List[TrendPoint] = [
            TrendPoint(
                cycle=int(cycles[i]),
                raw_value=round(float(raw_vals[i]), 4),
                rolling_mean=round(float(r_mean[i]), 4),
                rolling_std=round(float(r_std[i]), 4),
                rolling_min=round(float(r_min[i]), 4),
                rolling_max=round(float(r_max[i]), 4),
                rolling_slope=round(float(r_slope[i]), 6),
            )
            for i in range(total_cycles)
        ]

        is_downsampled = False
        if total_cycles > max_points and max_points >= 20:
            is_downsampled = True
            step = math.ceil(total_cycles / max_points)
            sampled = all_points[::step]
            # Ensure final critical failure/censored cycle is strictly present
            if sampled[-1].cycle != all_points[-1].cycle:
                sampled.append(all_points[-1])
            returned_points = sampled
        else:
            returned_points = all_points

        return SensorTrendResponse(
            machine_id=machine.machine_id,
            sensor_key=clean_sensor,
            channel_name=meta["name"],
            engineering_unit=meta["unit"],
            window_size=window,
            total_cycles=total_cycles,
            returned_points=len(returned_points),
            is_downsampled=is_downsampled,
            direction=direction,
            overall_slope=round(overall_slope, 6),
            points=returned_points,
        )

    def get_correlation(
        self,
        machine_id_str: str,
        channels: Optional[List[str]] = None,
    ) -> CorrelationMatrixResponse:
        machine = self._get_machine(machine_id_str)
        df = self._load_telemetry_df(machine.id)

        target_channels = channels if channels else [
            "sensor_2",
            "sensor_3",
            "sensor_4",
            "sensor_7",
            "sensor_8",
            "sensor_9",
            "sensor_11",
            "sensor_12",
            "sensor_14",
            "sensor_15",
            "sensor_20",
            "sensor_21",
        ]

        valid_channels = [ch for ch in target_channels if ch in ACTIVE_CHANNELS and ch in df.columns]
        if not valid_channels:
            raise ValidationException("No valid active channels provided for correlation matrix.")

        channel_names = [CHANNEL_METADATA.get(ch, {}).get("name", ch) for ch in valid_channels]

        if df.empty or len(df) < 2:
            identity = [[1.0 if i == j else 0.0 for j in range(len(valid_channels))] for i in range(len(valid_channels))]
            return CorrelationMatrixResponse(
                machine_id=machine.machine_id,
                channels=valid_channels,
                channel_names=channel_names,
                matrix=identity,
            )

        sub_df = df[valid_channels].astype(float)
        corr_matrix = sub_df.corr(method="pearson").fillna(0.0).to_numpy()

        # Clean NaN or rounding artifacts
        matrix_list = [
            [round(float(np.clip(corr_matrix[i, j], -1.0, 1.0)), 3) for j in range(len(valid_channels))]
            for i in range(len(valid_channels))
        ]

        return CorrelationMatrixResponse(
            machine_id=machine.machine_id,
            channels=valid_channels,
            channel_names=channel_names,
            matrix=matrix_list,
        )

    def get_feature_preview(
        self,
        machine_id_str: str,
        start_cycle: int = 1,
        end_cycle: int = 50,
        window: int = 20,
    ) -> FeaturePreviewResponse:
        """
        Generates the exact derived feature representation consumed downstream by the Phase 4 RUL model.
        Labeled explicitly as derived features, with zero ML predictions.
        """
        machine = self._get_machine(machine_id_str)
        df = self._load_telemetry_df(machine.id)

        if df.empty:
            return FeaturePreviewResponse(
                machine_id=machine.machine_id,
                feature_engineering_version="1.0.0",
                window_size=window,
                min_periods=1,
                scaling_policy="Fit strictly on INTERNAL_TRAIN (Units 1-80) during M4",
                total_feature_count=0,
                columns=[],
                rows=[],
            )

        # Slice bounded cycles
        cycles = df["source_cycle"].to_numpy(dtype=int)
        mask = (cycles >= start_cycle) & (cycles <= end_cycle)
        bounded_indices = np.where(mask)[0]

        columns_meta: List[FeatureColumnMeta] = []
        feature_dict_by_cycle: Dict[int, Dict[str, float]] = {int(c): {} for c in cycles[bounded_indices]}

        # Active channels (14 sensors + 2 op settings)
        for ch in ACTIVE_CHANNELS:
            vals = df[ch].to_numpy(dtype=float)
            r_mean, r_std, r_min, r_max, r_slope = RollingFeatureCalculator.calculate_rolling_features(
                cycles=cycles,
                values=vals,
                window=window,
            )

            feat_specs = [
                (f"{ch}_raw", "RAW", vals),
                (f"{ch}_rolling_mean_w{window}", "ROLLING_MEAN", r_mean),
                (f"{ch}_rolling_std_w{window}", "ROLLING_STD", r_std),
                (f"{ch}_rolling_min_w{window}", "ROLLING_MIN", r_min),
                (f"{ch}_rolling_max_w{window}", "ROLLING_MAX", r_max),
                (f"{ch}_rolling_slope_w{window}", "ROLLING_SLOPE", r_slope),
            ]

            for fname, ftype, arr in feat_specs:
                columns_meta.append(
                    FeatureColumnMeta(
                        name=fname,
                        source_channel=ch,
                        feature_type=ftype,
                        window=window if "w" in fname else 1,
                    )
                )
                for idx in bounded_indices:
                    c = int(cycles[idx])
                    feature_dict_by_cycle[c][fname] = round(float(arr[idx]), 4)

        rows = [
            FeaturePreviewRow(cycle=c, features=feature_dict_by_cycle[c])
            for c in sorted(feature_dict_by_cycle.keys())
        ]

        return FeaturePreviewResponse(
            machine_id=machine.machine_id,
            feature_engineering_version="1.0.0",
            window_size=window,
            min_periods=1,
            scaling_policy="Fit strictly on INTERNAL_TRAIN (Units 1-80) during M4",
            total_feature_count=len(columns_meta),
            columns=columns_meta,
            rows=rows,
        )

    def compare_machines(self, machine_ids: List[str]) -> MachineComparisonResponse:
        """
        Lightweight analytical comparison across machines (cycle count, sensor drift, volatility).
        Does NOT rank by risk or predict failure.
        """
        if not machine_ids or len(machine_ids) > 10:
            raise ValidationException("Please provide between 1 and 10 machine identifiers to compare.")

        items: List[MachineComparisonItem] = []
        for mid in machine_ids:
            try:
                m = self._get_machine(mid)
            except NotFoundException:
                continue

            df = self._load_telemetry_df(m.id)
            if df.empty:
                continue

            def calc_drift(col: str) -> float:
                if col in df.columns and len(df) > 1:
                    return round(float(df[col].iloc[-1] - df[col].iloc[0]), 4)
                return 0.0

            # Volatility score = average standard deviation across key temperatures
            key_cols = ["sensor_2", "sensor_3", "sensor_4", "sensor_7"]
            stds = [df[c].std() for c in key_cols if c in df.columns]
            vol_score = round(float(np.mean(stds)), 4) if stds else 0.0

            items.append(
                MachineComparisonItem(
                    machine_id=m.machine_id,
                    source_entity_id=m.source_entity_id,
                    split_category=m.split_category.value if hasattr(m.split_category, "value") else str(m.split_category),
                    status=m.status.value if hasattr(m.status, "value") else str(m.status),
                    total_cycles=m.total_cycles,
                    max_cycle=m.max_cycle,
                    ground_truth_rul=m.ground_truth_rul,
                    drift_t24=calc_drift("sensor_2"),
                    drift_t30=calc_drift("sensor_3"),
                    drift_t50=calc_drift("sensor_4"),
                    drift_p30=calc_drift("sensor_7"),
                    drift_nf=calc_drift("sensor_8"),
                    volatility_score=vol_score,
                )
            )

        return MachineComparisonResponse(machines=items, compared_count=len(items))

    def get_fleet_analytics_overview(self) -> FleetAnalyticsOverviewResponse:
        """Fleet-wide operational telemetry coverage and cycle distribution metrics."""
        machines = list(self.db.execute(select(Machine)).scalars().all())

        train_machines = [m for m in machines if m.split_category in (SplitCategory.INTERNAL_TRAIN, "INTERNAL_TRAIN")]
        val_machines = [m for m in machines if m.split_category in (SplitCategory.INTERNAL_VAL, "INTERNAL_VAL")]
        test_machines = [m for m in machines if m.split_category in (SplitCategory.EVAL_TEST, "EVAL_TEST")]

        train_all = train_machines + val_machines
        train_cycles = [m.total_cycles for m in train_all]
        test_cycles = [m.total_cycles for m in test_machines]

        avg_train = float(np.mean(train_cycles)) if train_cycles else 0.0
        min_train = int(np.min(train_cycles)) if train_cycles else 0
        max_train = int(np.max(train_cycles)) if train_cycles else 0

        avg_test = float(np.mean(test_cycles)) if test_cycles else 0.0
        min_test = int(np.min(test_cycles)) if test_cycles else 0
        max_test = int(np.max(test_cycles)) if test_cycles else 0

        # Cycle distribution buckets
        buckets = {
            "0-100 cycles": 0,
            "101-150 cycles": 0,
            "151-200 cycles": 0,
            "201-250 cycles": 0,
            "251-300 cycles": 0,
            "300+ cycles": 0,
        }
        for m in machines:
            c = m.total_cycles
            if c <= 100:
                buckets["0-100 cycles"] += 1
            elif c <= 150:
                buckets["101-150 cycles"] += 1
            elif c <= 200:
                buckets["151-200 cycles"] += 1
            elif c <= 250:
                buckets["201-250 cycles"] += 1
            elif c <= 300:
                buckets["251-300 cycles"] += 1
            else:
                buckets["300+ cycles"] += 1

        total_telemetry_cycles = sum(m.total_cycles for m in machines)

        return FleetAnalyticsOverviewResponse(
            total_machines=len(machines),
            total_cycles=total_telemetry_cycles,
            train_engines_count=len(train_machines),
            val_engines_count=len(val_machines),
            test_engines_count=len(test_machines),
            avg_train_cycles=round(avg_train, 1),
            min_train_cycles=min_train,
            max_train_cycles=max_train,
            avg_test_cycles=round(avg_test, 1),
            min_test_cycles=min_test,
            max_test_cycles=max_test,
            active_sensor_channels=ACTIVE_SENSORS,
            invariant_sensor_channels=INVARIANT_CHANNELS,
            cycle_distribution_buckets=buckets,
        )
