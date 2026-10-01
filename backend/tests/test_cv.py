import json
from pathlib import Path
import uuid
import numpy as np
from PIL import Image
import pytest
import torch

from backend.app.models.inspection import InspectionResult, InspectionRun
from backend.app.services.cv_model_service import (
    DEFAULT_DATASET_DIR,
    DEFAULT_MODEL_DIR,
    MODEL_VERSION,
    PatchCoreDetector,
)
from backend.app.api.v1.endpoints.inspections import _validate_safe_path, ALLOWED_STORAGE_ROOTS
from fastapi import HTTPException


def test_mvtec_dataset_structure_and_counts():
    """Validates the official MVTec AD metal_nut dataset structure, image counts, and ground-truth masks."""
    data_dir = DEFAULT_DATASET_DIR
    assert data_dir.exists(), f"Dataset directory {data_dir} does not exist"

    train_good = data_dir / "train" / "good"
    assert train_good.exists()
    train_good_images = list(train_good.glob("*.png"))
    assert len(train_good_images) == 220, f"Expected 220 train/good images, found {len(train_good_images)}"

    # Test split counts
    test_dir = data_dir / "test"
    expected_test_counts = {
        "good": 22,
        "bent": 25,
        "color": 22,
        "flip": 23,
        "scratch": 23,
    }
    total_test_count = 0
    for category, expected_count in expected_test_counts.items():
        cat_dir = test_dir / category
        assert cat_dir.exists(), f"Missing test category directory: {cat_dir}"
        cat_imgs = list(cat_dir.glob("*.png"))
        assert len(cat_imgs) == expected_count, f"Expected {expected_count} for {category}, found {len(cat_imgs)}"
        total_test_count += len(cat_imgs)

    assert total_test_count == 115, f"Expected 115 total test images, found {total_test_count}"

    # Ground truth masks counts
    gt_dir = data_dir / "ground_truth"
    expected_mask_counts = {
        "bent": 25,
        "color": 22,
        "flip": 23,
        "scratch": 23,
    }
    total_masks = 0
    for category, expected_count in expected_mask_counts.items():
        cat_gt = gt_dir / category
        assert cat_gt.exists(), f"Missing ground truth directory: {cat_gt}"
        cat_masks = list(cat_gt.glob("*.png"))
        assert len(cat_masks) == expected_count, f"Expected {expected_count} masks for {category}, found {len(cat_masks)}"
        total_masks += len(cat_masks)

    assert total_masks == 93, f"Expected 93 ground truth masks, found {total_masks}"


def test_split_isolation_and_no_leakage():
    """Asserts strict isolation: training directory contains ONLY normal good images; no defective images leak."""
    train_dir = DEFAULT_DATASET_DIR / "train"
    train_subdirs = [d.name for d in train_dir.iterdir() if d.is_dir()]
    assert train_subdirs == ["good"], f"Training directory must ONLY contain 'good' images, found {train_subdirs}"


def test_model_artifact_persistence_and_versions():
    """Asserts that model weights and metadata are persisted on disk with strict versioning."""
    config_file = DEFAULT_MODEL_DIR / "config.json"
    bank_file = DEFAULT_MODEL_DIR / "memory_bank.pt"

    assert config_file.exists(), f"Missing model config: {config_file}"
    assert bank_file.exists(), f"Missing memory bank: {bank_file}"

    with open(config_file) as f:
        meta = json.load(f)

    assert meta["model_version"] == MODEL_VERSION
    assert meta["backbone"] == "wide_resnet50_2"
    assert "feature_config_version" in meta
    assert "policy_version" in meta
    assert meta["threshold"] > 0
    assert meta["normal_stats"]["training_images_count"] == 220
    assert meta["normal_stats"]["subsample_ratio"] == 0.05
    assert meta["normal_stats"]["memory_bank_size"] == 8624

    bank_tensor = torch.load(bank_file, map_location="cpu")
    assert bank_tensor.shape == (8624, 1536)
    assert bank_tensor.dtype == torch.float32


def test_detector_inference_and_policy(tmp_path):
    """Verifies feature extraction, nearest neighbor scoring, threshold policy, and localization output."""
    detector = PatchCoreDetector(model_version=MODEL_VERSION)
    detector.load_model(model_dir=DEFAULT_MODEL_DIR)

    # Test on a real test image
    test_img_path = DEFAULT_DATASET_DIR / "test" / "good" / "000.png"
    pred = detector.predict_image(
        image=test_img_path,
        output_dir=tmp_path,
        image_identifier="test_000",
    )

    assert "image_level_score" in pred
    assert "decision" in pred
    assert pred["decision"] in ["PASS", "DEFECT"]
    assert abs(pred["threshold"] - detector.threshold) < 1e-3
    assert pred["heatmap_path"] is not None
    assert Path(pred["heatmap_path"]).exists()
    assert pred["overlay_path"] is not None
    assert Path(pred["overlay_path"]).exists()

    # Verify decision policy consistency
    if pred["image_level_score"] >= pred["threshold"]:
        assert pred["decision"] == "DEFECT"
    else:
        assert pred["decision"] == "PASS"


def test_api_list_inspections(client, viewer_token_headers):
    """Verifies GET /api/v1/inspections returns 200 and listed runs."""
    resp = client.get("/api/v1/inspections", headers=viewer_token_headers)
    assert resp.status_code == 200
    runs = resp.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1
    assert runs[0]["category"] == "metal_nut"
    assert runs[0]["model_version"] == MODEL_VERSION


def test_api_inspection_detail_and_summary(client, viewer_token_headers, db):
    """Verifies GET /api/v1/inspections/{id} and /summary return expected evaluation metrics."""
    run = db.query(InspectionRun).first()
    assert run is not None, "At least one inspection run should be persisted."

    resp = client.get(f"/api/v1/inspections/{run.id}", headers=viewer_token_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(run.id)
    assert data["total_images"] == 115

    sum_resp = client.get(f"/api/v1/inspections/{run.id}/summary", headers=viewer_token_headers)
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert "metrics" in sum_data
    assert "roc_auc" in sum_data["metrics"]
    assert sum_data["metrics"]["roc_auc"] > 0.95
    assert "defect_breakdown" in sum_data
    assert "bent" in sum_data["defect_breakdown"]


def test_api_inspection_results_filtering(client, viewer_token_headers, db):
    """Verifies GET /api/v1/inspections/{id}/results with filters."""
    run = db.query(InspectionRun).first()

    resp = client.get(
        f"/api/v1/inspections/{run.id}/results?defect_class=bent",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 25
    assert all(r["defect_class"] == "bent" for r in results)

    # Filter by decision
    resp_pass = client.get(
        f"/api/v1/inspections/{run.id}/results?decision=PASS",
        headers=viewer_token_headers,
    )
    assert resp_pass.status_code == 200
    pass_results = resp_pass.json()
    assert all(r["decision"] == "PASS" for r in pass_results)


def test_api_result_details_and_artifacts(client, viewer_token_headers, db):
    """Verifies single result retrieval and safe artifact streaming."""
    result = db.query(InspectionResult).filter(InspectionResult.heatmap_path.isnot(None)).first()
    assert result is not None

    # Result detail
    res_resp = client.get(f"/api/v1/inspections/results/{result.id}", headers=viewer_token_headers)
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert res_data["id"] == str(result.id)

    # Heatmap streaming
    hm_resp = client.get(f"/api/v1/inspections/results/{result.id}/heatmap", headers=viewer_token_headers)
    assert hm_resp.status_code == 200
    assert hm_resp.headers["content-type"] == "image/png"

    # Overlay streaming
    ov_resp = client.get(f"/api/v1/inspections/results/{result.id}/overlay", headers=viewer_token_headers)
    assert ov_resp.status_code == 200
    assert ov_resp.headers["content-type"] == "image/png"

    # Original image streaming
    orig_resp = client.get(f"/api/v1/inspections/results/{result.id}/original", headers=viewer_token_headers)
    assert orig_resp.status_code == 200
    assert orig_resp.headers["content-type"] == "image/png"


def test_api_path_traversal_protection():
    """Asserts that _validate_safe_path rejects directory traversal attempts."""
    # Attempt to access /etc/passwd or outside file
    with pytest.raises(HTTPException) as exc_info:
        _validate_safe_path("../../../../../etc/passwd", ALLOWED_STORAGE_ROOTS)
    assert exc_info.value.status_code in [403, 404]

    with pytest.raises(HTTPException) as exc_info:
        _validate_safe_path("/etc/passwd", ALLOWED_STORAGE_ROOTS)
    assert exc_info.value.status_code in [403, 404]


def test_api_rbac_run_inspection(client, viewer_token_headers):
    resp = client.post("/api/v1/inspections/run", headers=viewer_token_headers, json={"category": "metal_nut"})
    assert resp.status_code == 403
    body = resp.json()
    if "error" in body:
        assert body["error"]["code"] == "PERMISSION_DENIED" or "Insufficient permissions" in body["error"].get("message", "")
    else:
        assert "Insufficient permissions" in body.get("detail", "")

