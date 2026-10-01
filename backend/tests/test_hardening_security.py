import uuid
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings, settings
from backend.app.core.security import create_access_token
from backend.app.models.user import User, UserRole


# ==============================================================================
# Phase 2 — Authentication Hardening Tests
# ==============================================================================

def test_auth_missing_token_rejected(client: TestClient):
    """Endpoints requiring authentication reject unauthenticated requests."""
    response = client.get("/api/v1/machines")
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "detail" in data["error"] or "message" in data["error"]


def test_auth_invalid_token_rejected(client: TestClient):
    """Malformed or fabricated JWTs are strictly rejected with 401."""
    response = client.get(
        "/api/v1/machines",
        headers={"Authorization": "Bearer not-a-valid-token-string"}
    )
    assert response.status_code == 401
    assert "error" in response.json()


def test_auth_expired_token_rejected(client: TestClient, create_test_user):
    """Expired JWT tokens must be rejected with 401."""
    user = create_test_user()
    expired_payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    response = client.get(
        "/api/v1/machines",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    assert "error" in response.json()


def test_auth_inactive_user_token_rejected(client: TestClient, db, create_test_user):
    """Tokens for deactivated/inactive users cannot authenticate."""
    user = create_test_user()
    user.is_active = False
    db.commit()

    token = create_access_token(subject=str(user.id), role=user.role.value)
    response = client.get(
        "/api/v1/machines",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert "error" in response.json()


def test_auth_token_without_sub_rejected(client: TestClient):
    """Tokens missing subject identifier ('sub') must be rejected."""
    bad_payload = {
        "role": "ADMIN",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    bad_token = jwt.encode(bad_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    response = client.get(
        "/api/v1/machines",
        headers={"Authorization": f"Bearer {bad_token}"}
    )
    assert response.status_code == 401


# ==============================================================================
# Phase 3 — RBAC Hardening Tests
# ==============================================================================

def test_rbac_viewer_blocked_from_prediction_mutation(client: TestClient, viewer_token_headers):
    """Viewers cannot trigger or persist ML RUL predictions."""
    response = client.post(
        "/api/v1/machines/TURBOFAN-ENG-001/predictions",
        headers=viewer_token_headers,
        json={},
    )
    assert response.status_code == 403
    data = response.json()
    assert "error" in data


def test_rbac_viewer_blocked_from_risk_evaluation(client: TestClient, viewer_token_headers):
    """Viewers cannot trigger risk evaluations or state transitions."""
    response = client.post(
        "/api/v1/machines/TURBOFAN-ENG-001/risk/evaluate",
        headers=viewer_token_headers,
        json={},
    )
    assert response.status_code == 403


def test_rbac_viewer_blocked_from_alert_acknowledgement(client: TestClient, viewer_token_headers):
    """Viewers cannot acknowledge alerts."""
    fake_alert_id = str(uuid.uuid4())
    response = client.post(
        f"/api/v1/alerts/{fake_alert_id}/acknowledge",
        headers=viewer_token_headers,
        json={"comment": "Attempted viewer ack"},
    )
    assert response.status_code == 403


def test_rbac_viewer_blocked_from_work_order_creation(client: TestClient, viewer_token_headers):
    """Viewers cannot create maintenance work orders."""
    response = client.post(
        "/api/v1/maintenance/work-orders",
        headers=viewer_token_headers,
        json={
            "machine_id": "TURBOFAN-ENG-001",
            "title": "Unauthorized Maintenance",
            "priority": "HIGH",
            "source_domain": "MACHINE_HEALTH",
        },
    )
    assert response.status_code == 403


def test_rbac_operator_allowed_prediction_mutation(client: TestClient, operator_token_headers):
    """Operators can trigger real RUL predictions."""
    response = client.post(
        "/api/v1/machines/TURBOFAN-ENG-001/predictions",
        headers=operator_token_headers,
        json={"observation_cycle": 50},
    )
    assert response.status_code == 201
    assert "predicted_rul" in response.json()


# ==============================================================================
# Phase 4 & 5 — Input, File & Path Security Tests
# ==============================================================================

def test_sql_injection_machine_id_handled_safely(client: TestClient, viewer_token_headers):
    """SQL injection payloads in machine ID parameter return 404 cleanly, not 500."""
    sqli_payload = "TURBOFAN-ENG-001' OR '1'='1"
    response = client.get(
        f"/api/v1/machines/{sqli_payload}",
        headers=viewer_token_headers,
    )
    assert response.status_code in [400, 404]
    data = response.json()
    assert "Traceback" not in str(data)
    assert "syntax error" not in str(data).lower()


def test_path_traversal_blocked_in_inspection_artifacts(client: TestClient, viewer_token_headers):
    """Arbitrary non-existent, traversal, or malicious result paths return 404 or 422 cleanly."""
    traversal_id = "../../etc/passwd"
    response = client.get(
        f"/api/v1/inspections/results/{traversal_id}/original",
        headers=viewer_token_headers,
    )
    assert response.status_code in [400, 403, 404, 422]


def test_resource_abuse_compare_machines_bounded(client: TestClient, viewer_token_headers):
    """Comparing more than 10 machines at once is rejected to prevent resource exhaustion."""
    over_limit_ids = ",".join([f"TURBOFAN-ENG-{i:03d}" for i in range(1, 15)])
    response = client.get(
        f"/api/v1/machines/analytics/compare?machine_ids={over_limit_ids}",
        headers=viewer_token_headers,
    )
    assert response.status_code == 400
    assert "bounded to at most 10" in response.json()["error"]["message"]


def test_resource_abuse_compare_machines_empty_rejected(client: TestClient, viewer_token_headers):
    """Empty machine IDs list in compare is rejected."""
    response = client.get(
        "/api/v1/machines/analytics/compare?machine_ids=   ",
        headers=viewer_token_headers,
    )
    assert response.status_code == 400


def test_resource_abuse_feature_preview_cycles_validated(client: TestClient, viewer_token_headers):
    """Feature preview rejects end_cycle < start_cycle."""
    response = client.get(
        "/api/v1/machines/TURBOFAN-ENG-001/analytics/features?start_cycle=50&end_cycle=10",
        headers=viewer_token_headers,
    )
    assert response.status_code == 400


# ==============================================================================
# Phase 6 & 10 — Security Headers & Request Correlation Tests
# ==============================================================================

def test_security_headers_present(client: TestClient):
    """HTTP security headers are injected into all HTTP responses."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    headers = response.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "geolocation=()" in headers.get("Permissions-Policy", "")


def test_request_correlation_id_generated(client: TestClient):
    """Incoming requests without X-Request-ID receive a generated correlation ID."""
    response = client.get("/api/v1/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 10


def test_request_correlation_id_propagated(client: TestClient):
    """Incoming client-supplied X-Request-ID is preserved and returned."""
    custom_id = "test-corr-id-123456789"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.headers.get("X-Request-ID") == custom_id


# ==============================================================================
# Phase 17 — Health & Readiness Probes Tests
# ==============================================================================

def test_health_liveness_probe(client: TestClient):
    """Liveness probe confirms application process is running."""
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == "MachIntel"


def test_health_readiness_probe(client: TestClient):
    """Readiness probe verifies live PostgreSQL connectivity."""
    response = client.get("/api/v1/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "latency_ms" in data


# ==============================================================================
# Phase 2 & 13 — Production Configuration Security Tests
# ==============================================================================

def test_production_config_rejects_insecure_default_secret():
    """Settings must reject insecure default secret key when ENVIRONMENT is production."""
    with pytest.raises(ValueError, match="SECRET_KEY must be an environment-configured secret"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="insecure-dev-secret-key-change-in-production-min-32-chars-long",
            DEBUG=False,
        )


def test_production_config_rejects_debug_mode():
    """Settings must reject DEBUG=True when ENVIRONMENT is production."""
    with pytest.raises(ValueError, match="DEBUG must be set to False"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-sufficiently-long-and-secure-production-secret-key-32",
            DEBUG=True,
        )


def test_production_config_rejects_wildcard_cors():
    """Settings must reject wildcard CORS when credentials are enabled in production."""
    with pytest.raises(ValueError, match="wildcard CORS"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-sufficiently-long-and-secure-production-secret-key-32",
            DEBUG=False,
            BACKEND_CORS_ORIGINS=["*"],
        )


def test_production_config_accepts_valid_configuration():
    """Settings accepts valid secure production configuration."""
    cfg = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a-sufficiently-long-and-secure-production-secret-key-32",
        DEBUG=False,
        BACKEND_CORS_ORIGINS=["https://machintel.internal"],
    )
    assert cfg.ENVIRONMENT == "production"
    assert cfg.DEBUG is False
