import pytest
from fastapi.testclient import TestClient


def test_admin_endpoint_accessible_by_admin(client: TestClient, admin_token_headers):
    response = client.get("/api/v1/admin/users", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_admin_endpoint_forbidden_for_operator(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/admin/users", headers=operator_token_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_endpoint_forbidden_for_viewer(client: TestClient, viewer_token_headers):
    response = client.get("/api/v1/admin/users", headers=viewer_token_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_endpoint_unauthorized_without_token(client: TestClient):
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
