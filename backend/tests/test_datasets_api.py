import pytest
from fastapi.testclient import TestClient


def test_list_datasets(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/datasets", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1
    cmapss_item = next(item for item in data["items"] if item["dataset_name"] == "NASA_CMAPSS_FD001")
    assert cmapss_item["license"] == "Public Domain / NASA Open Data Policy"
    assert "train_FD001.txt" in cmapss_item["file_checksums"]


def test_get_dataset_by_name(client: TestClient, operator_token_headers):
    response = client.get(
        "/api/v1/datasets/NASA_CMAPSS_FD001",
        headers=operator_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_name"] == "NASA_CMAPSS_FD001"
    assert len(data["active_sensors"]) == 15
    assert len(data["invariant_sensors"]) == 7
    assert "sensor_1" in data["invariant_sensors"]


def test_get_dataset_not_found(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/datasets/NON_EXISTENT_DATASET", headers=operator_token_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
