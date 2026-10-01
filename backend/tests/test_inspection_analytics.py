import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.models.inspection import InspectionRun


def test_get_run_summary(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/inspection-analytics/runs/{run_id}/summary returns deterministic statistics."""
    run = db.query(InspectionRun).first()
    assert run is not None, "Real inspection run must be persisted."

    resp = client.get(
        f"/api/v1/inspection-analytics/runs/{run.id}/summary",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["run_id"] == str(run.id)
    assert data["total_images"] == 115
    assert data["passed_count"] == 27
    assert data["defect_count"] == 88
    assert abs(data["observed_defect_rate"] - (88 / 115)) < 1e-3
    assert data["threshold"] == 2.8155
    assert data["score_min"] > 2.0
    assert data["score_max"] < 5.0
    assert data["score_min"] <= data["score_median"] <= data["score_max"]
    assert "roc_auc" in data["evaluation_metrics"]
    assert data["evaluation_metrics"]["roc_auc"] > 0.98


def test_get_score_distribution(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/inspection-analytics/runs/{run_id}/scores generates histogram and percentiles."""
    run = db.query(InspectionRun).first()

    resp = client.get(
        f"/api/v1/inspection-analytics/runs/{run.id}/scores?bins=15",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["threshold"] == 2.8155
    assert "overall_stats" in data
    assert "normal_stats" in data
    assert "defective_stats" in data

    # Verify counts
    assert data["overall_stats"]["count"] == 115
    assert data["normal_stats"]["count"] == 22
    assert data["defective_stats"]["count"] == 93

    # Mean normal score should be significantly lower than mean defective score
    assert data["normal_stats"]["mean"] < data["defective_stats"]["mean"]

    # Verify histogram bin consistency
    histogram = data["histogram"]
    assert len(histogram) == 15
    total_in_bins = sum(b["total_count"] for b in histogram)
    assert total_in_bins == 115

    normal_in_bins = sum(b["normal_count"] for b in histogram)
    defect_in_bins = sum(b["defect_count"] for b in histogram)
    assert normal_in_bins == 22
    assert defect_in_bins == 93


def test_get_defect_class_analytics(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/inspection-analytics/runs/{run_id}/defects breaks down MVTec categories."""
    run = db.query(InspectionRun).first()

    resp = client.get(
        f"/api/v1/inspection-analytics/runs/{run.id}/defects",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == str(run.id)
    assert data["category"] == "metal_nut"

    classes_by_name = {c["defect_class"]: c for c in data["classes"]}
    expected_classes = ["bent", "color", "flip", "good", "scratch"]
    for exp_cls in expected_classes:
        assert exp_cls in classes_by_name, f"Missing class: {exp_cls}"

    # Verify exact MVTec test split image counts
    assert classes_by_name["bent"]["image_count"] == 25
    assert classes_by_name["color"]["image_count"] == 22
    assert classes_by_name["flip"]["image_count"] == 23
    assert classes_by_name["good"]["image_count"] == 22
    assert classes_by_name["scratch"]["image_count"] == 23

    # Check observed detection rate matches evaluated accuracy
    assert classes_by_name["flip"]["observed_detection_rate"] == 1.0  # 23/23 detected
    assert classes_by_name["bent"]["detected_count"] == 24
    assert classes_by_name["bent"]["missed_count"] == 1


def test_get_confusion_matrix(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/inspection-analytics/runs/{run_id}/confusion-matrix calculates classification metrics."""
    run = db.query(InspectionRun).first()

    resp = client.get(
        f"/api/v1/inspection-analytics/runs/{run.id}/confusion-matrix",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["true_positives"] == 87
    assert data["true_negatives"] == 21
    assert data["false_positives"] == 1
    assert data["false_negatives"] == 6
    assert abs(data["precision"] - (87 / 88)) < 1e-3
    assert abs(data["recall"] - (87 / 93)) < 1e-3
    assert abs(data["specificity"] - (21 / 22)) < 1e-3
    assert data["f1_score"] > 0.95
    assert data["image_roc_auc"] > 0.98
    assert data["threshold"] == 2.8155


def test_get_localization_analytics(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/inspection-analytics/runs/{run_id}/localization returns real pixel ROC-AUC."""
    run = db.query(InspectionRun).first()

    resp = client.get(
        f"/api/v1/inspection-analytics/runs/{run.id}/localization",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["has_localization"] is True
    assert data["pixel_roc_auc"] == 0.9769
    assert data["mask_evaluated_images"] == 93
    assert "PatchCore" in data["localization_method"]
    assert "224x224" in data["resolution"]


def test_get_run_provenance(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/inspection-analytics/runs/{run_id}/provenance exposes pipeline lineage."""
    run = db.query(InspectionRun).first()

    resp = client.get(
        f"/api/v1/inspection-analytics/runs/{run.id}/provenance",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["dataset_identifier"] == "MVTec-AD-metal_nut"
    assert data["model_version"] == "mvtec-patchcore-metalnut-v1.0.0"
    assert data["policy_version"] == "cv-policy-v1.0.0"
    assert data["threshold"] == 2.8155
    assert data["normal_training_stats"]["training_images_count"] == 220
    assert data["normal_training_stats"]["subsample_ratio"] == 0.05
    assert data["normal_training_stats"]["memory_bank_size"] == 8624


def test_compare_runs_single_run_behavior(client: TestClient, viewer_token_headers):
    """Verifies GET /api/v1/inspection-analytics/compare gracefully communicates insufficient runs."""
    resp = client.get(
        "/api/v1/inspection-analytics/compare",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # With only 1 run, comparison is not available
    assert data["is_available"] is False
    assert "requires at least two distinct inspection runs" in data["reason"]
    assert data["total_runs"] >= 1
    assert len(data["runs"]) >= 1


def test_list_runs_filtering(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/inspection-analytics/runs filtering."""
    run = db.query(InspectionRun).first()

    resp = client.get(
        f"/api/v1/inspection-analytics/runs?model_version={run.model_version}",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) >= 1
    assert all(r["model_version"] == run.model_version for r in runs)


def test_invalid_run_id_returns_404(client: TestClient, viewer_token_headers):
    """Verifies accessing non-existent run ID returns 404."""
    non_existent_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/inspection-analytics/runs/{non_existent_id}/summary",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 404
    body = resp.json()
    if "error" in body:
        assert body["error"]["code"] in ["NOT_FOUND", "HTTP_ERROR"]
        assert "not found" in body["error"]["message"].lower()
    else:
        assert "not found" in body["detail"].lower()


def test_unauthenticated_analytics_returns_401(client: TestClient):
    """Verifies accessing analytics endpoints without auth returns 401."""
    resp = client.get("/api/v1/inspection-analytics/runs")
    assert resp.status_code == 401
