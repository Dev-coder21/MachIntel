import pytest
from fastapi.testclient import TestClient
from backend.app.models.user import UserRole


def test_user_registration_success(client: TestClient):
    payload = {
        "email": "engineer.lead@example.com",
        "username": "lead_eng",
        "password": "StrongPassword2026!",
        "full_name": "Chief Reliability Engineer",
        "role": "OPERATOR",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["username"] == payload["username"]
    assert data["role"] == "OPERATOR"
    assert "id" in data
    # Ensure password hash is NEVER leaked in response
    assert "hashed_password" not in data
    assert "password" not in data


def test_user_registration_duplicate_email(client: TestClient, create_test_user):
    existing = create_test_user(email="duplicate@example.com")
    payload = {
        "email": "duplicate@example.com",
        "username": "different_username",
        "password": "AnotherPassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESOURCE_CONFLICT"


def test_login_success(client: TestClient, create_test_user):
    create_test_user(
        username="operator_bob",
        email="bob@example.com",
        password="MySecretPassword123!",
        role=UserRole.OPERATOR,
    )
    # Login via username
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "operator_bob", "password": "MySecretPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "operator_bob"

    # Login via email
    response_email = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "bob@example.com", "password": "MySecretPassword123!"},
    )
    assert response_email.status_code == 200


def test_login_invalid_credentials(client: TestClient, create_test_user):
    create_test_user(username="valid_user", password="CorrectPassword123!")
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "valid_user", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_get_current_user_me(client: TestClient, operator_token_headers):
    response = client.get("/api/v1/auth/me", headers=operator_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert data["role"] == "OPERATOR"


def test_get_current_user_unauthenticated(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
