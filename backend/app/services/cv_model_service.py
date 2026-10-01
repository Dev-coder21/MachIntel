from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
import torch
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as T

logger = logging.getLogger(__name__)

# Constants & Version Identifiers
MODEL_VERSION = "mvtec-patchcore-metalnut-v1.0.0"
FEATURE_CONFIG_VERSION = "cv-feature-config-v1.0.0"
POLICY_VERSION = "cv-policy-v1.0.0"
DEFAULT_CATEGORY = "metal_nut"
DEFAULT_DATASET_ID = "MVTec-AD-metal_nut"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_MODEL_DIR = PROJECT_ROOT / "storage" / "models" / "cv" / MODEL_VERSION
DEFAULT_INSPECTION_STORAGE_DIR = PROJECT_ROOT / "storage" / "inspections"
DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "raw" / "mvtec_ad" / "metal_nut"


class PatchCoreDetector:
    """
    PatchCore-style visual anomaly detector for industrial inspection.
    Backbone: Pretrained frozen WideResNet-50-2
    Feature extraction: intermediate convolutions from layer2 and layer3.
    Memory bank: constructed strictly from normal training images.
    Threshold: derived from normal reference distribution (mean + 3 * std).
    """

    def __init__(
        self,
        model_version: str = MODEL_VERSION,
        backbone_name: str = "wide_resnet50_2",
        feature_config_version: str = FEATURE_CONFIG_VERSION,
        policy_version: str = POLICY_VERSION,
        device: Optional[str] = None,
    ):
        self.model_version = model_version
        self.backbone_name = backbone_name
        self.feature_config_version = feature_config_version
        self.policy_version = policy_version

        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cpu")

        self.transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.avgpool = torch.nn.AvgPool2d(kernel_size=3, stride=1, padding=1)

        # Hook storage
        self._features: Dict[str, torch.Tensor] = {}
        self._model = self._init_backbone()

        # Anomaly detection state
        self.memory_bank: Optional[torch.Tensor] = None
        self._m_norm: Optional[torch.Tensor] = None
        self.threshold: float = 3.0
        self.normal_stats: Dict[str, float] = {}

    def _init_backbone(self) -> torch.nn.Module:
        logger.info(f"Loading pretrained backbone: {self.backbone_name}")
        model = models.wide_resnet50_2(weights=models.Wide_ResNet50_2_Weights.IMAGENET1K_V1)
        model.eval()
        for param in model.parameters():
            param.requires_grad = False

        def get_hook(name: str):
            def hook(module, input, output):
                self._features[name] = output
            return hook

        model.layer2.register_forward_hook(get_hook("layer2"))
        model.layer3.register_forward_hook(get_hook("layer3"))
        model.to(self.device)
        return model

    def extract_patch_embeddings(self, image: Union[Image.Image, Path, str]) -> Tuple[torch.Tensor, Tuple[int, int]]:
        """
        Extracts pooled patch embeddings of shape (H*W, 1536) from input image.
        """
        if isinstance(image, (str, Path)):
            pil_img = Image.open(image).convert("RGB")
        else:
            pil_img = image.convert("RGB")

        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            _ = self._model(tensor)

        l2 = self._features["layer2"]  # (1, 512, 28, 28)
        l3 = self._features["layer3"]  # (1, 1024, 14, 14)

        # Bilinear interpolation to align spatial dimensions
        l3_up = F.interpolate(l3, size=l2.shape[-2:], mode="bilinear", align_corners=False)
        combined = torch.cat([l2, l3_up], dim=1)  # (1, 1536, 28, 28)

        # Local neighborhood aggregation
        pooled = self.avgpool(combined)  # (1, 1536, 28, 28)
        b, c, h, w = pooled.shape
        patches = pooled.permute(0, 2, 3, 1).reshape(-1, c)  # (784, 1536)

        return patches, (h, w)

    def build_memory_bank(
        self,
        train_good_dir: Union[Path, str],
        subsample_ratio: float = 0.05,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Extracts patch embeddings from normal training images ONLY and constructs coreset memory bank.
        Calibrates threshold based on the normal training score distribution.
        """
        train_path = Path(train_good_dir)
        if not train_path.exists():
            raise FileNotFoundError(f"Training directory not found: {train_path}")

        image_files = sorted([f for f in train_path.iterdir() if f.suffix.lower() in [".png", ".jpg", ".jpeg"]])
        if not image_files:
            raise ValueError(f"No normal training images found in {train_path}")

        logger.info(f"Extracting patches from {len(image_files)} normal training images...")
        all_patches = []
        for img_file in image_files:
            p, _ = self.extract_patch_embeddings(img_file)
            all_patches.append(p)

        full_patch_tensor = torch.cat(all_patches, dim=0)  # (N_patches, 1536)
        total_patches = full_patch_tensor.shape[0]

        # Deterministic Coreset Subsampling
        n_subsample = max(1, int(total_patches * subsample_ratio))
        logger.info(f"Coreset subsampling: selecting {n_subsample}/{total_patches} patches ({subsample_ratio*100:.1f}%)")

        generator = torch.Generator().manual_seed(seed)
        subsample_indices = torch.randperm(total_patches, generator=generator)[:n_subsample]
        self.memory_bank = full_patch_tensor[subsample_indices].to(self.device)
        self._m_norm = (self.memory_bank ** 2).sum(dim=1, keepdim=True).t()

        # Calibration on normal training reference
        logger.info("Calibrating decision threshold on normal training images...")
        normal_scores = []
        for img_file in image_files:
            patches, _ = self.extract_patch_embeddings(img_file)
            score, _ = self._compute_patch_distances(patches)
            normal_scores.append(score.item())

        normal_scores_arr = np.array(normal_scores)
        mean_score = float(np.mean(normal_scores_arr))
        std_score = float(np.std(normal_scores_arr))
        max_score = float(np.max(normal_scores_arr))
        p95 = float(np.percentile(normal_scores_arr, 95))
        p99 = float(np.percentile(normal_scores_arr, 99))

        # Defensible calibration policy: mean + 3 * std (standard 3-sigma industrial process limit)
        # Guarantees < 0.3% theoretical false alarm rate on Gaussian normal process
        calibrated_threshold = float(mean_score + 3.0 * std_score)

        self.threshold = calibrated_threshold
        self.normal_stats = {
            "training_images_count": len(image_files),
            "total_patches_extracted": total_patches,
            "memory_bank_size": n_subsample,
            "subsample_ratio": subsample_ratio,
            "subsample_seed": seed,
            "normal_score_mean": round(mean_score, 4),
            "normal_score_std": round(std_score, 4),
            "normal_score_max": round(max_score, 4),
            "normal_score_p95": round(p95, 4),
            "normal_score_p99": round(p99, 4),
            "calibrated_threshold": round(calibrated_threshold, 4),
            "calibration_policy": "mean + 3 * std (normal reference)",
        }

        logger.info(f"Calibration complete: Threshold = {self.threshold:.4f} (mean={mean_score:.4f}, std={std_score:.4f})")
        return self.normal_stats

    def _compute_patch_distances(self, patches: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Computes minimum Euclidean distance from each patch to the memory bank.
        Returns:
            max_distance: scalar image-level anomaly score
            patch_min_distances: (N_patches,) minimum distance for each patch
        """
        if self.memory_bank is None or self._m_norm is None:
            raise RuntimeError("Memory bank is not initialized. Build or load model first.")

        p_norm = (patches ** 2).sum(dim=1, keepdim=True)
        dot = torch.mm(patches, self.memory_bank.t())
        dist_sq = torch.clamp(p_norm + self._m_norm - 2 * dot, min=0.0)
        dists = torch.sqrt(dist_sq)

        min_dists, _ = torch.min(dists, dim=1)
        max_dist = torch.max(min_dists)
        return max_dist, min_dists

    def predict_image(
        self,
        image: Union[Image.Image, Path, str],
        output_dir: Optional[Union[Path, str]] = None,
        image_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs real anomaly detection on a single image.
        Computes image-level anomaly score, PASS/DEFECT decision, and generates
        pixel-level heatmap and visual overlay if output_dir is provided.
        """
        start_time = time.perf_counter()

        if isinstance(image, (str, Path)):
            pil_img = Image.open(image).convert("RGB")
        else:
            pil_img = image.convert("RGB")

        patches, (h, w) = self.extract_patch_embeddings(pil_img)
        max_score, patch_dists = self._compute_patch_distances(patches)

        image_score = float(max_score.item())
        decision = "DEFECT" if image_score >= self.threshold else "PASS"

        # Generate pixel-level anomaly map
        dist_grid = patch_dists.reshape(1, 1, h, w)  # (1, 1, 28, 28)
        upsampled = F.interpolate(dist_grid, size=(224, 224), mode="bilinear", align_corners=False)
        raw_map = upsampled.squeeze().cpu().numpy()

        # Gaussian smoothing
        smoothed_map = gaussian_filter(raw_map, sigma=4.0)

        # Normalize map for visualization
        map_min, map_max = smoothed_map.min(), smoothed_map.max()
        if map_max - map_min > 1e-6:
            norm_map = (smoothed_map - map_min) / (map_max - map_min)
        else:
            norm_map = np.zeros_like(smoothed_map)

        heatmap_path = None
        overlay_path = None

        if output_dir:
            out_p = Path(output_dir)
            heatmaps_dir = out_p / "heatmaps"
            overlays_dir = out_p / "overlays"
            heatmaps_dir.mkdir(parents=True, exist_ok=True)
            overlays_dir.mkdir(parents=True, exist_ok=True)

            img_id = image_identifier or f"img_{uuid.uuid4().hex[:8]}"

            # Generate colormapped heatmap
            cmap = plt.colormaps.get_cmap("jet")
            colored_map = (cmap(norm_map)[:, :, :3] * 255).astype(np.uint8)
            heatmap_img = Image.fromarray(colored_map)

            heatmap_file = heatmaps_dir / f"{img_id}_heatmap.png"
            heatmap_img.save(heatmap_file)
            heatmap_path = str(heatmap_file)

            # Generate overlay blending with resized original
            resized_orig = pil_img.resize((224, 224))
            orig_np = np.array(resized_orig)
            overlay_np = (0.55 * orig_np + 0.45 * colored_map).astype(np.uint8)
            overlay_img = Image.fromarray(overlay_np)

            overlay_file = overlays_dir / f"{img_id}_overlay.png"
            overlay_img.save(overlay_file)
            overlay_path = str(overlay_file)

        inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "image_level_score": round(image_score, 4),
            "threshold": round(self.threshold, 4),
            "decision": decision,
            "anomaly_map_max": round(float(map_max), 4),
            "anomaly_map_min": round(float(map_min), 4),
            "raw_anomaly_map": raw_map,  # for pixel-level metric calculation
            "heatmap_path": heatmap_path,
            "overlay_path": overlay_path,
            "inference_metadata": {
                "model_version": self.model_version,
                "backbone": self.backbone_name,
                "feature_layers": ["layer2", "layer3"],
                "subsample_ratio": self.normal_stats.get("subsample_ratio", 0.05),
                "device": str(self.device),
                "inference_time_ms": inference_time_ms,
            },
        }

    def save_model(self, model_dir: Union[Path, str] = DEFAULT_MODEL_DIR):
        """Persists the memory bank tensor and configuration metadata to disk."""
        target_dir = Path(model_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        if self.memory_bank is None:
            raise ValueError("Cannot save model: memory bank is empty.")

        torch.save(self.memory_bank.cpu(), target_dir / "memory_bank.pt")

        metadata = {
            "model_version": self.model_version,
            "backbone": self.backbone_name,
            "feature_config_version": self.feature_config_version,
            "policy_version": self.policy_version,
            "threshold": self.threshold,
            "normal_stats": self.normal_stats,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(target_dir / "config.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Model saved successfully to {target_dir}")

    def load_model(self, model_dir: Union[Path, str] = DEFAULT_MODEL_DIR):
        """Loads a persisted PatchCore memory bank and configuration."""
        target_dir = Path(model_dir)
        config_file = target_dir / "config.json"
        bank_file = target_dir / "memory_bank.pt"

        if not config_file.exists() or not bank_file.exists():
            raise FileNotFoundError(f"Model files not found in {target_dir}")

        with open(config_file, "r") as f:
            metadata = json.load(f)

        self.model_version = metadata.get("model_version", self.model_version)
        self.backbone_name = metadata.get("backbone", self.backbone_name)
        self.feature_config_version = metadata.get("feature_config_version", self.feature_config_version)
        self.policy_version = metadata.get("policy_version", self.policy_version)
        self.threshold = float(metadata.get("threshold", 3.0))
        self.normal_stats = metadata.get("normal_stats", {})

        self.memory_bank = torch.load(bank_file, map_location=self.device)
        self._m_norm = (self.memory_bank ** 2).sum(dim=1, keepdim=True).t()

        logger.info(f"Loaded PatchCore model '{self.model_version}' with threshold {self.threshold:.4f}")

    def evaluate_dataset(
        self,
        dataset_dir: Union[Path, str] = DEFAULT_DATASET_DIR,
        run_id: Optional[str] = None,
        storage_dir: Union[Path, str] = DEFAULT_INSPECTION_STORAGE_DIR,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Runs full evaluation against the official MVTec AD test split.
        Computes image-level and pixel-level metrics, defect category breakdown,
        and generates persisted inspection artifacts.
        """
        run_uuid = run_id or str(uuid.uuid4())
        run_storage = Path(storage_dir) / run_uuid
        run_storage.mkdir(parents=True, exist_ok=True)

        data_root = Path(dataset_dir)
        test_dir = data_root / "test"
        gt_dir = data_root / "ground_truth"

        if not test_dir.exists():
            raise FileNotFoundError(f"Test directory not found at {test_dir}")

        defect_classes = sorted([d.name for d in test_dir.iterdir() if d.is_dir()])
        logger.info(f"Evaluating official test split across categories: {defect_classes}")

        all_results: List[Dict[str, Any]] = []
        y_true_img: List[int] = []
        y_score_img: List[float] = []

        # Pixel-level evaluation storage
        pixel_true: List[np.ndarray] = []
        pixel_pred: List[np.ndarray] = []

        defect_breakdown: Dict[str, Dict[str, Any]] = {}

        for defect_cls in defect_classes:
            cls_dir = test_dir / defect_cls
            img_files = sorted([f for f in cls_dir.iterdir() if f.suffix.lower() in [".png", ".jpg"]])

            is_defect = (defect_cls != "good")
            gt_label = "DEFECT" if is_defect else "PASS"

            cls_scores = []
            cls_pass_count = 0
            cls_defect_count = 0

            for img_path in img_files:
                img_name = img_path.name
                item_id = f"{defect_cls}_{img_path.stem}"

                # Real inference — no ground truth access!
                pred = self.predict_image(
                    image=img_path,
                    output_dir=run_storage,
                    image_identifier=item_id,
                )

                score = pred["image_level_score"]
                decision = pred["decision"]

                y_true_img.append(1 if is_defect else 0)
                y_score_img.append(score)
                cls_scores.append(score)

                if decision == "PASS":
                    cls_pass_count += 1
                else:
                    cls_defect_count += 1

                # Ground truth mask reference (for evaluation ONLY)
                gt_mask_path = None
                has_gt_mask = False
                if is_defect:
                    # MVTec ground truth naming pattern: <stem>_mask.png
                    candidate_masks = [
                        gt_dir / defect_cls / f"{img_path.stem}_mask.png",
                        gt_dir / defect_cls / f"{img_path.stem}.png",
                    ]
                    for cm in candidate_masks:
                        if cm.exists():
                            gt_mask_path = str(cm)
                            has_gt_mask = True
                            # Compute pixel-level ROC component
                            mask_img = Image.open(cm).convert("L").resize((224, 224))
                            mask_arr = (np.array(mask_img) > 128).astype(np.uint8).flatten()
                            pred_arr = pred["raw_anomaly_map"].flatten()
                            pixel_true.append(mask_arr)
                            pixel_pred.append(pred_arr)
                            break

                all_results.append({
                    "id": str(uuid.uuid4()),
                    "run_id": run_uuid,
                    "split": "test",
                    "defect_class": defect_cls,
                    "source_image_path": str(img_path),
                    "source_image_filename": img_name,
                    "image_level_score": score,
                    "decision": decision,
                    "ground_truth_label": gt_label,
                    "heatmap_path": pred["heatmap_path"],
                    "overlay_path": pred["overlay_path"],
                    "ground_truth_mask_path": gt_mask_path,
                    "has_heatmap": pred["heatmap_path"] is not None,
                    "has_overlay": pred["overlay_path"] is not None,
                    "has_ground_truth_mask": has_gt_mask,
                    "inference_metadata": pred["inference_metadata"],
                    "created_at": datetime.now(timezone.utc),
                })

            cls_total = len(img_files)
            accuracy = (cls_defect_count / cls_total) if is_defect else (cls_pass_count / cls_total)
            defect_breakdown[defect_cls] = {
                "total_images": cls_total,
                "passed_count": cls_pass_count,
                "defect_count": cls_defect_count,
                "accuracy": round(accuracy, 4),
                "mean_score": round(float(np.mean(cls_scores)), 4),
                "min_score": round(float(np.min(cls_scores)), 4),
                "max_score": round(float(np.max(cls_scores)), 4),
            }

        # Calculate Image-Level Metrics
        y_true_np = np.array(y_true_img)
        y_score_np = np.array(y_score_img)
        y_pred_np = (y_score_np >= self.threshold).astype(int)

        roc_auc = float(roc_auc_score(y_true_np, y_score_np))
        pr_auc = float(average_precision_score(y_true_np, y_score_np))
        precision = float(precision_score(y_true_np, y_pred_np, zero_division=0))
        recall = float(recall_score(y_true_np, y_pred_np, zero_division=0))
        f1 = float(f1_score(y_true_np, y_pred_np, zero_division=0))

        cm = confusion_matrix(y_true_np, y_pred_np)
        tn, fp, fn, tp = cm.ravel()

        # Calculate Pixel-Level ROC-AUC if masks were evaluated
        pixel_roc_auc = None
        if pixel_true and pixel_pred:
            flat_pixel_true = np.concatenate(pixel_true)
            flat_pixel_pred = np.concatenate(pixel_pred)
            try:
                pixel_roc_auc = float(roc_auc_score(flat_pixel_true, flat_pixel_pred))
            except Exception as e:
                logger.warning(f"Could not compute pixel ROC-AUC: {e}")

        evaluation_summary = {
            "model_version": self.model_version,
            "feature_config_version": self.feature_config_version,
            "policy_version": self.policy_version,
            "dataset_identifier": DEFAULT_DATASET_ID,
            "category": DEFAULT_CATEGORY,
            "threshold": round(self.threshold, 4),
            "normal_stats": self.normal_stats,
            "total_images_evaluated": len(all_results),
            "passed_count": int(np.sum(y_pred_np == 0)),
            "defect_count": int(np.sum(y_pred_np == 1)),
            "image_level_metrics": {
                "roc_auc": round(roc_auc, 4),
                "pr_auc": round(pr_auc, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "confusion_matrix": {
                    "true_negative": int(tn),
                    "false_positive": int(fp),
                    "false_negative": int(fn),
                    "true_positive": int(tp),
                },
            },
            "pixel_level_metrics": {
                "pixel_roc_auc": round(pixel_roc_auc, 4) if pixel_roc_auc is not None else None,
                "mask_evaluated_images": len(pixel_true),
            },
            "defect_breakdown": defect_breakdown,
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Save run summary JSON to artifact storage
        summary_file = run_storage / "evaluation_summary.json"
        with open(summary_file, "w") as f:
            json.dump(evaluation_summary, f, indent=2)

        return evaluation_summary, all_results
