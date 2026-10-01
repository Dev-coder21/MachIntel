# MVTec Anomaly Detection (AD) Dataset: Metal Nut Specification

## 1. Overview & Provenance

The **MVTec Anomaly Detection (MVTec AD)** benchmark is the industry standard dataset for visual defect detection and optical surface inspection (Bergmann et al., *CVPR 2019*). 

In MachIntel Phase 6 (Milestone M6), the **`metal_nut`** category was ingested to establish the project's first genuine Computer Vision vertical slice.

- **Dataset Identifier**: `MVTec-AD-metal_nut`
- **Category**: `metal_nut`
- **Source**: Official MVTec AD benchmark / Hugging Face mirror snapshot
- **Image Resolution**: $700 \times 700$ pixels, 8-bit RGB lossless PNG
- **License**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)

---

## 2. Directory Layout & Structure

The dataset is ingested into `data/raw/mvtec_ad/metal_nut/` maintaining the exact canonical MVTec AD structure:

```
data/raw/mvtec_ad/
    metal_nut/
        train/
            good/                     # 220 normal training images
        test/
            good/                     # 22 normal test images
            bent/                     # 25 defective test images
            color/                    # 22 defective test images
            flip/                     # 23 defective test images
            scratch/                  # 23 defective test images
        ground_truth/
            bent/                     # 25 pixel-level binary defect masks
            color/                    # 22 pixel-level binary defect masks
            flip/                     # 23 pixel-level binary defect masks
            scratch/                  # 23 pixel-level binary defect masks
```

---

## 3. Verified Image & Mask Counts

| Split / Folder | Subfolder / Class | Image Count | Mask Count | Split Purpose |
| :--- | :--- | :---: | :---: | :--- |
| **Train** | `good` | 220 | 0 | Normal Reference & Memory Bank |
| **Test** | `good` | 22 | 0 | Normal Validation |
| **Test** | `bent` | 25 | 25 | Structural / Deformation Defect Evaluation |
| **Test** | `color` | 22 | 22 | Oxidation / Chemical Contamination Evaluation |
| **Test** | `flip` | 23 | 23 | Assembly / Orientation Inversion Evaluation |
| **Test** | `scratch` | 23 | 23 | Surface Mechanical Defect Evaluation |
| **Total** | — | **335 Images** | **93 Masks** | Official Split Unchanged |

*Note on counts*: An early typographical summary cited 357 images ($220 + 115 + 22 = 357$), which inadvertently added the test good count twice. The ground-truth count of the official MVTec AD benchmark is exactly **335 unique images** (220 training + 115 evaluation) and **93 pixel masks**, as verified by checksums and directory inspection.

---

## 4. Zero-Leakage Policy & Split Integrity

1. **Training Partition Isolation**:
   The memory bank and the process threshold are constructed strictly from `train/good` images ($N = 220$). No test images—neither normal test nor defective test—are ever exposed during model training or threshold calibration.
2. **Evaluation Ground Truth Isolation**:
   The official ground-truth defect masks and defect category labels are strictly held out for computing evaluation metrics (e.g., Pixel ROC-AUC, classification confusion matrix). Under no circumstances are ground-truth masks or labels passed to the prediction pipeline.
3. **No Reshuffling**:
   The official MVTec train/test split is preserved intact without arbitrary random resplits.
