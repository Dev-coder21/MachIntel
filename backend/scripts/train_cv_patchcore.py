#!/usr/bin/env python3
"""
Offline Training / Memory Bank Construction & Threshold Calibration
for MVTec AD metal_nut PatchCore Anomaly Detector.

Usage:
    python backend/scripts/train_cv_patchcore.py
"""

import argparse
import logging
from pathlib import Path
import sys

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.cv_model_service import (
    DEFAULT_DATASET_DIR,
    DEFAULT_MODEL_DIR,
    MODEL_VERSION,
    PatchCoreDetector,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_cv_patchcore")


def train_patchcore(
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    output_dir: Path = DEFAULT_MODEL_DIR,
    subsample_ratio: float = 0.05,
    seed: int = 42,
):
    train_good_dir = dataset_dir / "train" / "good"
    if not train_good_dir.exists():
        logger.error(f"Normal training directory not found at: {train_good_dir}")
        logger.error("Run backend/scripts/download_mvtec.py first to fetch the official dataset.")
        sys.exit(1)

    images = list(train_good_dir.glob("*.png"))
    logger.info(f"=== Starting PatchCore Model Construction ({MODEL_VERSION}) ===")
    logger.info(f"Target Dataset: MVTec AD (category: metal_nut)")
    logger.info(f"Normal Training Images: {len(images)}")
    logger.info(f"Coreset Subsampling Ratio: {subsample_ratio*100:.1f}% (Seed: {seed})")

    detector = PatchCoreDetector(model_version=MODEL_VERSION)
    calibration_stats = detector.build_memory_bank(
        train_good_dir=train_good_dir,
        subsample_ratio=subsample_ratio,
        seed=seed,
    )

    detector.save_model(model_dir=output_dir)

    logger.info("=== Model Construction & Calibration Successful ===")
    logger.info(f"Memory Bank Patches: {calibration_stats['memory_bank_size']}")
    logger.info(f"Normal Score Mean:   {calibration_stats['normal_score_mean']}")
    logger.info(f"Normal Score Std:    {calibration_stats['normal_score_std']}")
    logger.info(f"Calibrated Threshold:{calibration_stats['calibrated_threshold']}")
    logger.info(f"Artifacts persisted to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and calibrate MVTec metal_nut PatchCore model")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--subsample-ratio", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    train_patchcore(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        subsample_ratio=args.subsample_ratio,
        seed=args.seed,
    )
