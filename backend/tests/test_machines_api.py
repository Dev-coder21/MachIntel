import pytest
from fastapi.testclient import TestClient


def test_list_machines_authenticated(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/machines?limit=10", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 200
    assert len(data["items"]) == 10
    assert data["items"][0]["machine_type"] == "TURBOFAN_ENGINE"


def test_list_machines_split_filter(client: TestClient, operator_token_headers):
    # Test INTERNAL_TRAIN filter (Units 1-80)
    response_train = client.get(
        "/api/v1/machines?split_category=INTERNAL_TRAIN&limit=100",
        headers=operator_token_headers,
    )
    assert response_train.status_code == 200
    assert response_train.json()["total"] == 80

    # Test INTERNAL_VAL filter (Units 81-100)
    response_val = client.get(
        "/api/v1/machines?split_category=INTERNAL_VAL&limit=100",
        headers=operator_token_headers,
    )
    assert response_val.status_code == 200
    assert response_val.json()["total"] == 20

    # Test EVAL_TEST filter (100 test units)
    response_test = client.get(
        "/api/v1/machines?split_category=EVAL_TEST&limit=100",
        headers=operator_token_headers,
    )
    assert response_test.status_code == 200
    assert response_test.json()["total"] == 100


def test_list_machines_search(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/machines?search=042", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Matches TURBOFAN-ENG-042 and TURBOFAN-ENG-TEST-042
    assert data["total"] == 2
    for item in data["items"]:
        assert "042" in item["machine_id"]


def test_get_machine_detail(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/machines/TURBOFAN-ENG-001", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "TURBOFAN-ENG-001"
    assert data["source_dataset"] == "NASA_CMAPSS_FD001"
    assert data["source_entity_id"] == "1"
    assert data["split_category"] == "INTERNAL_TRAIN"
    assert data["total_cycles"] == 192
    assert len(data["active_sensor_channels"]) == 15
    assert len(data["invariant_sensor_channels"]) == 7


def test_get_machine_telemetry(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/telemetry?start_cycle=1&end_cycle=10&limit=10",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "TURBOFAN-ENG-001"
    assert data["returned_records"] == 10
    assert len(data["records"]) == 10
    # Check cycle ordering
    cycles = [r["source_cycle"] for r in data["records"]]
    assert cycles == list(range(1, 11))
    # Verify no fabricated timestamps (event_timestamp must be None)
    assert data["records"][0]["event_timestamp"] is None
    # Check sensor values are numeric
    assert isinstance(data["records"][0]["sensor_2"], float)


def test_get_machine_not_found(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/machines/NON-EXISTENT-999", headers=operator_token_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_get_machine_telemetry_limit_validation(client: TestClient, operator_token_headers):
    # Limit exceeds maximum allowed 500
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/telemetry?limit=999",
        headers=operator_token_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_foundation_stats(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/machines/stats/summary", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_machines"] == 200
    assert data["total_telemetry_records"] == 33727
    assert data["datasets_registered"] >= 1
    assert data["operational_count"] >= 1
