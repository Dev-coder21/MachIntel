# MVTec AD Metal Nut Benchmark Evaluation Report

## 1. Evaluation Methodology

The model `mvtec-patchcore-metalnut-v1.0.0` was evaluated against the complete, un-reshuffled official MVTec AD `metal_nut` test split.

- **Total Test Images**: 115
- **Normal Test Images (`good`)**: 22
- **Defective Test Images**: 93 (bent: 25, color: 22, flip: 23, scratch: 23)
- **Ground Truth Defect Masks**: 93
- **Calibrated Threshold ($\tau$)**: **2.8155**

---

## 2. Image-Level Anomaly Detection Metrics

| Metric | Result | Interpretation |
| :--- | :---: | :--- |
| **ROC-AUC (Image-Level)** | **0.9858** | Near-perfect separation across normal and defective parts |
| **PR-AUC (Precision-Recall)** | **0.9967** | High defect precision across recall spectrum |
| **Precision** | **0.9886** | 87 of 88 predicted defects were genuine defects |
| **Recall (Sensitivity)** | **0.9355** | 87 of 93 defective components detected |
| **F1-Score** | **0.9613** | Harmonic balance between precision and recall |

### Confusion Matrix ($\tau = 2.8155$)

| | Actual Normal (`PASS`) | Actual Defect (`DEFECT`) |
| :--- | :---: | :---: |
| **Predicted `PASS`** | **21 (TN)** | **6 (FN)** |
| **Predicted `DEFECT`** | **1 (FP)** | **87 (TP)** |

- **False Alarm Rate (1 - Specificity)**: $1 / 22 = 4.5\%$ (21 of 22 normal parts correctly passed).
- **False Negative Rate**: $6 / 93 = 6.45\%$ (6 subtle micro-defects fell below the conservative 3-sigma process boundary).

---

## 3. Defect Category Breakdown

| Defect Class | Total Images | Passed (`PASS`) | Detected (`DEFECT`) | Category Accuracy | Score (Mean / Min / Max) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FLIP** | 23 | 0 | **23** | **100.0%** | 3.77 / 3.60 / 4.04 |
| **BENT** | 25 | 1 | **24** | **96.0%** | 3.51 / 2.72 / 4.16 |
| **COLOR** | 22 | 1 | **21** | **95.5%** | 3.48 / 2.60 / 4.05 |
| **GOOD** (Normal) | 22 | **21** | 1 | **95.5%** | 2.54 / 2.33 / 2.84 |
| **SCRATCH** | 23 | 4 | **19** | **82.6%** | 3.28 / 2.64 / 3.76 |

### Defect Sensitivity Observations
1. **Geometric & Orientation Anomalies (`flip`, `bent`)**:
   Achieve 96–100% detection. Orientation flip shifts macroscopic patch locations, generating high Euclidean distances ($> 3.60$) well above threshold.
2. **Surface Color Contamination (`color`)**:
   Achieves 95.5% detection with high separation ($3.48$ mean score vs $2.8155$ threshold).
3. **Subtle Surface Scratches (`scratch`)**:
   Represents fine-grained, localized defects where only a small cluster of patches deviate slightly from nominal surface texture. 19 of 23 scratches were caught; 4 hairline scratches had localized scores between $2.64$ and $2.80$, lying within the nominal $3\sigma$ upper tail.

---

## 4. Pixel-Level Localization Metrics

- **Pixel ROC-AUC**: **0.9769**
- **Evaluated Defect Masks**: 93 pixel masks (resized to $224 \times 224$)
- **Interpretation**: PatchCore intermediate feature distances reliably localize the exact pixels responsible for surface defects with $>97.6\%$ area under the ROC curve.
