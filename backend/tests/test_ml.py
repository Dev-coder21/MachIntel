import numpy as np
import pytest
from sqlalchemy import select

from backend.app.ml.metrics import calculate_phm_score, calculate_rmse
from backend.app.ml.rul_dataset import RUL_MAX_CAP
from backend.app.models.machine import Machine, SplitCategory
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.prediction import OperationalState, Prediction
from backend.app.services.prediction_service import (
    PredictionService,
    derive_operational_state,
)


def test_rmse_metric():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 30.0])
    # squared diffs: 4, 4, 0 -> mean = 8/3 -> sqrt = ~1.63299
    rmse = calculate_rmse(y_true, y_pred)
    assert round(rmse, 4) == round(np.sqrt(8.0 / 3.0), 4)


def test_phm_score_asymmetric_property():
    """
    NASA/PHM 2008 scoring function must penalize late predictions (d > 0)
    much more severely than early predictions (d < 0).
    """
    y_true = np.array([50.0])
    
    # 5 cycles early (d = -5): exp(5/13) - 1 ≈ 0.469
    early_pred = np.array([45.0])
    early_score = calculate_phm_score(y_true, early_pred)

    # 5 cycles late (d = +5): exp(5/10) - 1 ≈ 0.6487
    late_pred = np.array([55.0])
    late_score = calculate_phm_score(y_true, late_pred)

    assert late_score > early_score
    assert round(early_score, 3) == 0.469
    assert round(late_score, 3) == 0.649


def test_phm_score_zero_error():
    y_true = np.array([100.0, 50.0])
    y_pred = np.array([100.0, 50.0])
    assert calculate_phm_score(y_true, y_pred) == 0.0


def test_rul_target_clipping():
    total_cycle = 200
    cycles = np.array([1, 50, 100, 150, 199, 200])
    raw_rul = total_cycle - cycles
    clipped_rul = np.minimum(RUL_MAX_CAP, np.maximum(0, raw_rul))

    # At cycle 1: raw = 199 -> clipped to 125
    assert clipped_rul[0] == 125.0
    # At cycle 50: raw = 150 -> clipped to 125
    assert clipped_rul[1] == 125.0
    # At cycle 100: raw = 100 -> unclipped 100
    assert clipped_rul[2] == 100.0
    # At cycle 150: raw = 50 -> unclipped 50
    assert clipped_rul[3] == 50.0
    # At cycle 200: raw = 0 -> unclipped 0
    assert clipped_rul[5] == 0.0


def test_train_validation_entity_isolation(db):
    train_engines = list(
        db.execute(
            select(Machine).where(Machine.split_category == SplitCategory.INTERNAL_TRAIN)
        ).scalars().all()
    )
    val_engines = list(
        db.execute(
            select(Machine).where(Machine.split_category == SplitCategory.INTERNAL_VAL)
        ).scalars().all()
    )
    test_engines = list(
        db.execute(
            select(Machine).where(Machine.split_category == SplitCategory.EVAL_TEST)
        ).scalars().all()
    )

    train_ids = {m.machine_id for m in train_engines}
    val_ids = {m.machine_id for m in val_engines}
    test_ids = {m.machine_id for m in test_engines}

    assert len(train_ids) == 80
    assert len(val_ids) == 20
    assert len(test_ids) == 100

    # Ensure zero entity overlap across splits
    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)


def test_health_index_and_operational_state_mapping():
    assert derive_operational_state(0.85) == OperationalState.NORMAL
    assert derive_operational_state(0.70) == OperationalState.NORMAL
    assert derive_operational_state(0.69) == OperationalState.WATCH
    assert derive_operational_state(0.40) == OperationalState.WATCH
    assert derive_operational_state(0.39) == OperationalState.ELEVATED
    assert derive_operational_state(0.15) == OperationalState.ELEVATED
    assert derive_operational_state(0.14) == OperationalState.CRITICAL
    assert derive_operational_state(0.0) == OperationalState.CRITICAL


def test_model_registry_records(db):
    models = list(db.execute(select(ModelRegistry)).scalars().all())
    assert len(models) >= 2

    model_ids = {m.model_id for m in models}
    assert "rul-randomforest-v1.0.0" in model_ids
    assert "rul-ridge-v1.0.0" in model_ids

    active_models = [m for m in models if m.is_active and (getattr(m, "domain", None) in ("MACHINE_HEALTH", None))]
    assert len(active_models) == 1
    assert active_models[0].model_id == "rul-randomforest-v1.0.0"

    rf = next(m for m in models if m.model_id == "rul-randomforest-v1.0.0")
    assert "val_rmse" in rf.metrics
    assert "test_rmse" in rf.metrics
    assert "val_phm_score" in rf.metrics
    assert "test_phm_score" in rf.metrics
    assert len(rf.feature_names) == 102
    assert rf.window_size == 20


def test_prediction_service_inference(db):
    svc = PredictionService(db)
    pred = svc.predict_machine_health("TURBOFAN-ENG-001", persist=False)

    assert pred.machine_id is not None
    assert pred.predicted_rul >= 0.0
    assert 0.0 <= pred.health_index <= 1.0
    assert pred.operational_state in [s.value for s in OperationalState]
    assert pred.feature_engineering_version == "1.0.0"
    assert pred.observation_cycle == 192


def test_temporal_leakage_safeguard(db):
    """
    Ensure feature vectors at cycle t do NOT use future telemetry.
    Features computed with end_cycle=50 must match exact features when querying full dataset at cycle 50.
    """
    svc = PredictionService(db)
    feat_service = svc.feature_service

    df_truncated = feat_service.extract_features_df("TURBOFAN-ENG-001", end_cycle=50)
    df_full = feat_service.extract_features_df("TURBOFAN-ENG-001")

    row_truncated = df_truncated[df_truncated["source_cycle"] == 50].iloc[0]
    row_full = df_full[df_full["source_cycle"] == 50].iloc[0]

    feature_cols = feat_service.get_feature_names()
    for col in feature_cols:
        val_trunc = row_truncated[col]
        val_full = row_full[col]
        assert np.isclose(val_trunc, val_full, rtol=1e-5, atol=1e-5), f"Leakage detected on {col}"


def test_api_get_models(client, operator_token_headers):
    response = client.get("/api/v1/models", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert data["active_model_id"] == "rul-randomforest-v1.0.0"
    assert len(data["items"]) >= 2


def test_api_get_single_model(client, operator_token_headers):
    response = client.get("/api/v1/models/rul-randomforest-v1.0.0", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == "rul-randomforest-v1.0.0"
    assert data["algorithm"] == "RandomForestRegressor"
    assert data["is_active"] is True
    assert "val_rmse" in data["metrics"]


def test_api_predictions_flow(client, operator_token_headers):
    # 1. POST inference for TURBOFAN-ENG-002 at cycle 100
    post_res = client.post(
        "/api/v1/machines/TURBOFAN-ENG-002/predictions",
        json={"observation_cycle": 100},
        headers=operator_token_headers,
    )
    assert post_res.status_code == 201
    pred_data = post_res.json()
    assert pred_data["observation_cycle"] == 100
    assert pred_data["predicted_rul"] >= 0.0
    assert 0.0 <= pred_data["health_index"] <= 1.0

    # 2. GET latest prediction
    latest_res = client.get(
        "/api/v1/machines/TURBOFAN-ENG-002/predictions/latest",
        headers=operator_token_headers,
    )
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data is not None
    assert latest_data["machine_name"] == "TURBOFAN-ENG-002"

    # 3. GET paginated prediction history
    history_res = client.get(
        "/api/v1/machines/TURBOFAN-ENG-002/predictions?page=1&page_size=10",
        headers=operator_token_headers,
    )
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["total"] >= 1
    assert len(history_data["items"]) >= 1


def test_api_fleet_prognostics_overview(client, operator_token_headers):
    response = client.get("/api/v1/predictions/fleet/overview", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_machines"] == 200
    assert data["machines_with_predictions"] >= 1
    assert data["active_model_id"] == "rul-randomforest-v1.0.0"
    assert "NORMAL" in data["state_distribution"]
    assert "CRITICAL" in data["state_distribution"]


def test_api_invalid_observation_cycle(client, operator_token_headers):
    response = client.post(
        "/api/v1/machines/TURBOFAN-ENG-001/predictions",
        json={"observation_cycle": 99999},
        headers=operator_token_headers,
    )
    assert response.status_code == 400
    err_body = response.json()
    err_msg = err_body.get("error", {}).get("message", "") or err_body.get("detail", "")
    assert "out of bounds" in err_msg.lower()


def test_api_nonexistent_machine_returns_404(client, operator_token_headers):
    response = client.post(
        "/api/v1/machines/NON-EXISTENT-ENGINE/predictions",
        json={"observation_cycle": 10},
        headers=operator_token_headers,
    )
    assert response.status_code == 404
