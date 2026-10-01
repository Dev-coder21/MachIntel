import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.services.analytics_service import (
    ACTIVE_CHANNELS,
    ACTIVE_SENSORS,
    INVARIANT_CHANNELS,
    RollingFeatureCalculator,
)
from backend.app.services.feature_service import FeatureEngineeringContract, FeatureExtractionService


def test_rolling_feature_calculator_math():
    """Deterministic mathematical verification of rolling metrics."""
    cycles = np.array([1, 2, 3, 4, 5])
    values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])

    r_mean, r_std, r_min, r_max, r_slope = RollingFeatureCalculator.calculate_rolling_features(
        cycles=cycles,
        values=values,
        window=3,
    )

    # At cycle 1: single point
    assert r_mean[0] == 10.0
    assert r_std[0] == 0.0
    assert r_min[0] == 10.0
    assert r_max[0] == 10.0
    assert r_slope[0] == 0.0

    # At cycle 2: window of [10.0, 20.0]
    assert r_mean[1] == 15.0
    assert pytest.approx(r_std[1], 0.01) == 7.071
    assert r_min[1] == 10.0
    assert r_max[1] == 20.0
    assert pytest.approx(r_slope[1], 0.01) == 10.0  # (20 - 10) / (2 - 1)

    # At cycle 5: window of [30.0, 40.0, 50.0] (window=3)
    assert r_mean[4] == 40.0
    assert pytest.approx(r_std[4], 0.01) == 10.0
    assert r_min[4] == 30.0
    assert r_max[4] == 50.0
    assert pytest.approx(r_slope[4], 0.01) == 10.0


def test_rolling_feature_temporal_causality():
    """
    Verifies zero temporal leakage:
    Mutating future values (cycles 10..20) must have zero effect on rolling features at cycle <= 9.
    """
    cycles = np.arange(1, 21)
    base_values = np.linspace(100.0, 200.0, 20)

    # Calculate baseline
    m_base, s_base, min_base, max_base, sl_base = RollingFeatureCalculator.calculate_rolling_features(
        cycles=cycles,
        values=base_values,
        window=5,
    )

    # Create mutated future series (drastically altering values from index 10 onwards)
    mutated_values = base_values.copy()
    mutated_values[10:] = 9999.0

    m_mut, s_mut, min_mut, max_mut, sl_mut = RollingFeatureCalculator.calculate_rolling_features(
        cycles=cycles,
        values=mutated_values,
        window=5,
    )

    # Features at cycles 1 through 10 (indices 0..9) MUST be identical
    np.testing.assert_array_almost_equal(m_base[:10], m_mut[:10])
    np.testing.assert_array_almost_equal(s_base[:10], s_mut[:10])
    np.testing.assert_array_almost_equal(min_base[:10], min_mut[:10])
    np.testing.assert_array_almost_equal(max_base[:10], max_mut[:10])
    np.testing.assert_array_almost_equal(sl_base[:10], sl_mut[:10])


def test_machine_boundary_isolation(db):
    """
    Verifies that feature extraction for Machine 1 and Machine 2 are completely isolated
    and do not bleed cycle values or statistics across engine boundaries.
    """
    svc = FeatureExtractionService(db)
    df_m1 = svc.extract_features_df("TURBOFAN-ENG-001")
    df_m2 = svc.extract_features_df("TURBOFAN-ENG-002")

    # M1 has 192 cycles, M2 has 287 cycles
    assert len(df_m1) == 192
    assert len(df_m2) == 287

    # Ensure source cycles start at 1 and end at respective max
    assert df_m1["source_cycle"].iloc[0] == 1
    assert df_m1["source_cycle"].iloc[-1] == 192
    assert df_m2["source_cycle"].iloc[0] == 1
    assert df_m2["source_cycle"].iloc[-1] == 287

    # Features at cycle 1 for both machines must have rolling_std = 0.0
    assert df_m1["sensor_2_rolling_std_w20"].iloc[0] == 0.0
    assert df_m2["sensor_2_rolling_std_w20"].iloc[0] == 0.0


def test_feature_engineering_contract():
    """Verifies that the M4 ML contract defines exactly 96 features across 16 active channels."""
    contract = FeatureEngineeringContract()
    assert contract.window_size == 20
    assert contract.min_periods == 1
    assert len(contract.active_sensors) == 15
    assert len(contract.active_op_settings) == 2
    assert len(contract.invariant_channels) == 7

    # Invariant channels must never be in active set
    for inv in contract.invariant_channels:
        assert inv not in contract.active_sensors
        assert inv not in contract.active_op_settings


def test_analytics_summary_api(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/analytics/summary",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "TURBOFAN-ENG-001"
    assert data["total_cycles"] == 192
    assert data["first_cycle"] == 1
    assert data["latest_cycle"] == 192
    assert data["active_sensor_count"] == 15
    assert data["invariant_sensor_count"] == 7
    assert len(data["sensors"]) == len(ACTIVE_CHANNELS)
    assert len(data["top_drifting_sensors"]) <= 5


def test_analytics_sensors_api(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/analytics/sensors",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(ACTIVE_CHANNELS)
    t24 = next(s for s in data if s["sensor_key"] == "sensor_2")
    assert t24["channel_name"] == "Total Temperature at LPC Outlet"
    assert t24["min_value"] <= t24["max_value"]


def test_analytics_trends_api(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/analytics/trends?sensor=sensor_2&window=20",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "TURBOFAN-ENG-001"
    assert data["sensor_key"] == "sensor_2"
    assert data["window_size"] == 20
    assert len(data["points"]) > 0
    # First point check
    p0 = data["points"][0]
    assert p0["cycle"] == 1
    assert p0["rolling_std"] == 0.0


def test_analytics_trends_invariant_sensor_rejected(client: TestClient, operator_token_headers):
    # Sensor 1 is invariant in FD001 and should be rejected
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/analytics/trends?sensor=sensor_1&window=20",
        headers=operator_token_headers,
    )
    assert response.status_code == 422
    assert "invariant" in response.json()["error"]["message"].lower()


def test_analytics_correlation_api(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/analytics/correlation",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "TURBOFAN-ENG-001"
    matrix = data["matrix"]
    n = len(data["channels"])
    assert len(matrix) == n
    assert len(matrix[0]) == n
    # Diagonal of correlation matrix should be 1.0
    for i in range(n):
        assert pytest.approx(matrix[i][i], 0.01) == 1.0


def test_analytics_features_preview_api(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/analytics/features?start_cycle=1&end_cycle=10&window=20",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "TURBOFAN-ENG-001"
    assert data["window_size"] == 20
    assert data["total_feature_count"] == len(ACTIVE_CHANNELS) * 6  # 16 * 6 = 96
    assert len(data["rows"]) == 10
    assert "DERIVED ANALYTICAL FEATURES ONLY" in data["disclaimer"]


def test_fleet_analytics_overview_api(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/machines/analytics/overview",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_machines"] == 200
    assert data["total_cycles"] == 33727
    assert data["train_engines_count"] == 80
    assert data["val_engines_count"] == 20
    assert data["test_engines_count"] == 100
    assert data["min_train_cycles"] >= 100


def test_machine_comparison_api(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/machines/analytics/compare?machine_ids=TURBOFAN-ENG-001,TURBOFAN-ENG-002",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["compared_count"] == 2
    assert len(data["machines"]) == 2
    m1 = data["machines"][0]
    assert m1["machine_id"] == "TURBOFAN-ENG-001"
    assert isinstance(m1["drift_t24"], float)
