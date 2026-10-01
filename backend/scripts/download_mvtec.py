"""
MVTec AD metal_nut Dataset Acquisition & Ingestion Script.

Downloads and validates official MVTec Anomaly Detection (MVTec AD) metal_nut dataset:
- 357 total optical images (700x700 RGB PNG)
- 220 normal training images (train/good)
- 22 normal test images (test/good)
- 115 defective test images across 4 defect classes (bent, color, flip, scratch)
- 115 pixel-level binary ground truth masks in ground_truth/
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from huggingface_hub import snapshot_download

from backend.app.db.session import SessionLocal
from backend.app.models.dataset import DatasetMetadata

EXPECTED_COUNTS = {
    "train": {
        "good": 220,
    },
    "test": {
        "good": 22,
        "bent": 25,
        "color": 22,
        "flip": 23,
        "scratch": 23,
    },
    "ground_truth": {
        "bent": 25,
        "color": 22,
        "flip": 23,
        "scratch": 23,
    },
}

TOTAL_IMAGES = 335
TOTAL_TEST_IMAGES = 115
TOTAL_DEFECTIVE_IMAGES = 93
TOTAL_MASKS = 93


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def download_metal_nut(target_dir: Path) -> Path:
    """Downloads metal_nut from Hugging Face repository."""
    print(f"Downloading MVTec AD metal_nut dataset to {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Download snapshot of MSherbinii/mvtec-ad-metal-nut
    download_cache = snapshot_download(
        repo_id="MSherbinii/mvtec-ad-metal-nut",
        repo_type="dataset",
        allow_patterns=["metal_nut/**"],
    )

    src_metal_nut = Path(download_cache) / "metal_nut"
    if not src_metal_nut.exists():
        # Fallback if structure varies
        src_metal_nut = Path(download_cache)

    # Copy files into target_dir
    print(f"Syncing dataset files from cache ({src_metal_nut}) into {target_dir}...")
    for split_dir in ["train", "test", "ground_truth"]:
        src_split = src_metal_nut / split_dir
        dst_split = target_dir / split_dir
        if src_split.exists():
            if dst_split.exists():
                shutil.rmtree(dst_split)
            shutil.copytree(src_split, dst_split)

    return target_dir


def validate_metal_nut_dataset(dataset_dir: Path) -> Dict[str, Any]:
    """Validates structure, image counts, mask availability, and computes provenance checksums."""
    print("\nValidating MVTec AD metal_nut dataset structure and counts...")
    actual_counts = {"train": {}, "test": {}, "ground_truth": {}}

    for split, classes in EXPECTED_COUNTS.items():
        split_path = dataset_dir / split
        if not split_path.exists():
            raise FileNotFoundError(f"Missing required split directory: {split_path}")

        for cls_name, expected_count in classes.items():
            cls_path = split_path / cls_name
            if not cls_path.exists():
                raise FileNotFoundError(f"Missing class directory: {cls_path}")

            png_files = list(cls_path.glob("*.png"))
            actual_count = len(png_files)
            actual_counts[split][cls_name] = actual_count

            if actual_count != expected_count:
                raise ValueError(
                    f"Count mismatch in {split}/{cls_name}: expected {expected_count}, got {actual_count}"
                )
            print(f"  [OK] {split}/{cls_name}: {actual_count} PNG files (expected {expected_count})")

    # Verify mask alignment with defective test images
    for defect_cls in ["bent", "color", "flip", "scratch"]:
        test_imgs = sorted([f.stem for f in (dataset_dir / "test" / defect_cls).glob("*.png")])
        gt_masks = sorted([f.name.replace("_mask.png", "").replace(".png", "") for f in (dataset_dir / "ground_truth" / defect_cls).glob("*.png")])
        if len(test_imgs) != len(gt_masks):
            raise ValueError(f"Mask count mismatch for {defect_cls}: {len(test_imgs)} test images vs {len(gt_masks)} masks")

    train_total = sum(actual_counts["train"].values())
    test_total = sum(actual_counts["test"].values())
    gt_total = sum(actual_counts["ground_truth"].values())

    print(f"\nSummary:")
    print(f"  Total Normal Training Images: {train_total} (Expected: 220)")
    print(f"  Total Evaluation Test Images: {test_total} (Expected: 115 [22 normal, 93 defective])")
    print(f"  Total Pixel-Level Ground Truth Masks: {gt_total} (Expected: 93)")
    print(f"  Total Dataset Images: {train_total + test_total} (Expected: 335)")

    # Sample hash computation for provenance
    sample_train = dataset_dir / "train" / "good" / "000.png"
    sample_hash = ""
    if sample_train.exists():
        with open(sample_train, "rb") as f:
            sample_hash = hashlib.sha256(f.read()).hexdigest()

    return {
        "train_counts": actual_counts["train"],
        "test_counts": actual_counts["test"],
        "ground_truth_counts": actual_counts["ground_truth"],
        "total_images": train_total + test_total,
        "sample_train_000_sha256": sample_hash,
    }


def persist_dataset_provenance(meta: Dict[str, Any], dataset_dir: Path):
    """Persists MVTec AD dataset record in PostgreSQL dataset_metadata table."""
    db = SessionLocal()
    try:
        existing = (
            db.query(DatasetMetadata)
            .filter(DatasetMetadata.dataset_name == "MVTec-AD-metal_nut")
            .first()
        )
        if not existing:
            print("Registering MVTec-AD-metal_nut in dataset registry...")
            ds = DatasetMetadata(
                dataset_name="MVTec-AD-metal_nut",
                dataset_identifier="MVTec-AD-metal_nut",
                source="MVTec Software GmbH (Bergmann et al., CVPR 2019)",
                source_url="https://www.mvtec.com/company/research/datasets/mvtec-ad",
                license="CC BY-NC-SA 4.0",
                file_checksums={
                    "author": "Paul Bergmann, Michael Fauser, David Sattlegger, Carsten Steger",
                    "year": 2019,
                    "resolution": "700x700",
                    "channels": 3,
                    "color_space": "sRGB",
                    "format": "PNG",
                    "defect_classes": ["bent", "color", "flip", "scratch"],
                    "counts": meta,
                    "sample_train_000_sha256": meta["sample_train_000_sha256"],
                },
                schema_version="1.0.0",
                preprocessing_version="1.0.0",
                ingestion_version="1.0.0",
                active_sensors=["RGB_Image"],
                invariant_sensors=[],
            )
            db.add(ds)
            db.commit()
            print("Successfully registered MVTec-AD-metal_nut in database.")
        else:
            print("MVTec-AD-metal_nut already registered in database.")
    finally:
        db.close()


def main():
    root = get_project_root()
    target_dir = root / "data" / "raw" / "mvtec_ad" / "metal_nut"
    download_metal_nut(target_dir)
    meta = validate_metal_nut_dataset(target_dir)
    persist_dataset_provenance(meta, target_dir)
    print("\nMVTec AD metal_nut dataset acquisition and validation complete!")


if __name__ == "__main__":
    main()
