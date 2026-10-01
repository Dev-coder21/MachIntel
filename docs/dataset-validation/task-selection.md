# MachIntel Task Selection & Mathematical Formulation

**Document Version:** 1.0 (Phase 0 Validation Sprint)  
**Maintained By:** MachIntel Engineering Core  
**Review Standard:** Section 6 & Section 7 of MachIntel Master Blueprint  

---

## 1. Machine Health Prognostics Task Selection

### 1.1 Comparative Analysis of Candidate Machine Health Tasks

| Task Formulation | Target Output | Operational Value | Dataset Support (C-MAPSS) | Verdict & Rationale |
|---|---|---|---|---|
| **Binary Failure Classification** | $P(\text{failure in } W \text{ cycles}) \in [0, 1]$ | Medium. Actionable alert if window $W$ is well-chosen. | Artificial. Requires setting an arbitrary cutoff threshold (e.g. $W=30$ cycles). Creates severe class imbalance. | **Rejected as Primary.** Too coarse; loses continuous degradation trajectory. |
| **Pure Unsupervised Anomaly Detection** | Anomaly Score $s(t) \in [0, \infty)$ | Moderate. Detects deviation from initial baseline. | Weak. Does not estimate when failure will occur; sensitive to early sensor noise. | **Rejected as Primary.** Does not provide maintenance planning horizons. |
| **Remaining Useful Life (RUL) Regression** | Predicted remaining operating cycles $\widehat{RUL}(t) \in \mathbb{R}^+$ | **Very High.** Core metric for maintenance scheduling, parts ordering, and fleet dispatch. | **Native.** Ground-truth RUL is directly derivable from run-to-failure cycle trajectories and test ground-truth vector. | **SELECTED as Primary Task.** Most rigorous and actionable prognostic task. |
| **Derived Health Index (HI)** | Normalized machine condition score $HI(t) \in [0.0, 1.0]$ | **Exceptional.** Universal metric across operators, dashboards, and risk rules. | Directly maps from predicted RUL and baseline operational parameters. | **SELECTED as Companion Task.** Powers the MachIntel Fleet Dashboard and Risk Engine. |

---

### 1.2 Mathematical Formulation: Piecewise-Linear RUL Target
In turbofan engines, physical components do not degrade detectably from their very first flight cycle. For initial operational cycles, the engine remains in a stable healthy state; observable degradation only initiates after mechanical wear passes an internal threshold.

Following established PHM literature (Heimes et al., Zheng et al.), MachIntel adopts the **Piecewise-Linear RUL Target Function**:

$$RUL^*(t) = \min(RUL_{max}, \, T_{fail} - t)$$

- $T_{fail}$: Final recorded operational cycle for the engine unit (where functional failure occurred).
- $t$: Current operational flight cycle ($1 \le t \le T_{fail}$).
- $RUL_{max}$: Maximum degradation horizon plateau, set to **125 cycles** for C-MAPSS FD001.

```
RUL (cycles)
  125 |--------------------\  (Plateau: Nominal Healthy Operation)
      |                     \
      |                      \
      |                       \  (Linear Degradation Phase)
      |                        \
    0 +-------------------------\-----> Time in Cycles (t)
                                 T_fail
```

### 1.3 Derived Health Index ($HI$) Formulation
To power user-facing command center dashboards and automated risk alerts, predicted RUL is normalized into a continuous **Health Index**:

$$HI(t) = \min\left(1.0, \, \max\left(0.0, \, \frac{\widehat{RUL}(t)}{RUL_{max}}\right)\right)$$

#### Operational Risk State Mapping:
- **$HI(t) \ge 0.70$ $\rightarrow$ `NORMAL`:** Equipment operates within nominal tolerances.
- **$0.40 \le HI(t) < 0.70$ $\rightarrow$ `WATCH`:** Detectable degradation initiated; log trend and monitor.
- **$0.15 \le HI(t) < 0.40$ $\rightarrow$ `ELEVATED`:** Significant wear detected; schedule maintenance inspection.
- **$HI(t) < 0.15$ $\rightarrow$ `CRITICAL`:** High failure probability; trigger immediate maintenance intervention.

---

### 1.4 Machine Health Evaluation Metrics

#### 1. Root Mean Squared Error (RMSE)
Standard quadratic penalty on prognostic error:

$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N \left(\widehat{RUL}_i - RUL_i\right)^2}$$

#### 2. NASA Asymmetric PHM Scoring Function
In industrial aviation, predicting that an engine has *more* remaining life than it actually does (late prediction, $\widehat{RUL} > RUL$) is catastrophic because it leads to in-flight engine failure. Conversely, predicting failure slightly *early* ($\widehat{RUL} < RUL$) merely triggers premature inspection:

$$S = \sum_{i=1}^N s_i, \quad s_i = \begin{cases} 
e^{-\frac{\widehat{RUL}_i - RUL_i}{13}} - 1 & \text{if } \widehat{RUL}_i < RUL_i \quad (\text{Early prediction}) \\ 
e^{\frac{\widehat{RUL}_i - RUL_i}{10}} - 1 & \text{if } \widehat{RUL}_i \ge RUL_i \quad (\text{Late prediction / Hazard}) 
\end{cases}$$

---

### 1.5 Machine Health Baseline Strategy
1. **Non-ML Naive Baseline:** Constant mean RUL predictor based on training cycle distributions ($\overline{RUL}_{train}$).
2. **First ML Model (Phase 4):**
   - **Feature Extraction:** Sliding temporal window ($W = 20$ cycles). For each active sensor channel, compute:
     - Rolling Mean: $\mu_{W}(t)$
     - Rolling Standard Deviation: $\sigma_{W}(t)$
     - Rolling Linear Trend (Slope): $\beta_{W}(t)$
     - Min and Max within window: $\min_{W}(t), \max_{W}(t)$
   - **Algorithms:** Ridge Regression (interpretable linear baseline) and Random Forest Regressor (non-linear baseline).

---

## 2. Industrial Computer Vision Task Selection

### 2.1 Comparative Analysis of Candidate Vision Tasks

| Task Formulation | Target Output | Operational Value | Dataset Support (MVTec AD) | Verdict & Rationale |
|---|---|---|---|---|
| **Supervised Multi-Class Defect Classifier** | Probabilities across defect classes (`bent`, `color`, etc.) | Low. Fails when a novel or uncataloged manufacturing defect appears. | Misaligned. MVTec training sets contain zero defect images; supervised training violates the industrial premise. | **Rejected.** Unrealistic in true manufacturing lines where defects cannot be sampled beforehand. |
| **Unsupervised Anomaly Detection & Defect Localization** | Image Anomaly Score $S \in [0, 1]$ + Pixel Heatmap/Mask $M(x, y)$ | **Exceptional.** Flags any anomalous part without requiring prior defect examples, and precisely highlights where the defect is located. | **Native.** Designed specifically for MVTec AD's normal-only training set and pixel-level ground-truth test masks. | **SELECTED as Primary CV Task.** Matches the real-world manufacturing inspection paradigm. |

---

### 2.2 Mathematical Formulation: Anomaly Scoring & Localization
For an input inspection image $X \in \mathbb{R}^{H \times W \times 3}$:

1. **Feature Representation:**
   The image is passed through a pre-trained feature extractor $f_\theta$ (e.g. WideResNet-50-2 stages 2 and 3), producing a dense grid of patch feature embeddings:
   $$\mathcal{F}(X) = \{p_{h, w} \in \mathbb{R}^D \mid 1 \le h \le H', 1 \le w \le W'\}$$

2. **Pixel-Level Anomaly Map:**
   Each patch embedding $p_{h, w}$ is compared against the nominal memory bank $\mathcal{M}_{nominal}$ established from training images:
   $$\text{score}(p_{h, w}) = \min_{m \in \mathcal{M}_{nominal}} \|p_{h, w} - m\|_2$$
   The resulting spatial grid is bilinearly upsampled to original image dimensions $(H, W)$ and smoothed with a Gaussian filter:
   $$M(x, y) = \text{GaussianFilter}\left(\text{Upsample}(\text{score}(p))\right)$$

3. **Image-Level Anomaly Score:**
   The overall part anomaly score is defined by the maximum localized anomaly magnitude:
   $$S_{image} = \max_{x, y} M(x, y)$$

4. **Defect Decision Contract:**
   $$\text{Result} = \begin{cases} \text{DEFECT} & \text{if } S_{image} \ge \tau \\ \text{PASS} & \text{if } S_{image} < \tau \end{cases}$$
   where $\tau$ is calibrated on the nominal validation partition such that nominal False Positive Rate $\le 1\%$.

---

### 2.3 Computer Vision Evaluation Metrics

#### 1. Image-Level AUROC (Area Under ROC Curve)
Evaluates the model's ability to distinguish defective parts from nominal parts across all possible classification thresholds.

#### 2. Pixel-Level AUROC
Evaluates localization precision across all pixels in defective test images against ground-truth binary masks.

#### 3. Per-Region Overlap (PRO) Curve
Measures the average overlap proportion between connected defect components in ground-truth masks and predicted anomaly maps up to a maximum False Positive Rate of 30%:
$$\text{PRO} = \frac{1}{|\mathcal{C}|} \sum_{C_k \in \mathcal{C}} \frac{|C_k \cap P|}{|C_k|}$$
where $\mathcal{C}$ is the set of all ground-truth connected defect regions and $P$ is the predicted binary defect mask.

---

### 2.4 Computer Vision Baseline Strategy
1. **First CV Model (Phase 6):**
   - **PatchCore / Deep Nearest-Neighbor Memory Bank:**
     - Backbone: ImageNet pre-trained WideResNet-50-2 (frozen weights, no training backpropagation needed).
     - Patch Extraction: Locally neighborhood-aggregated features from mid-level convolutional layers.
     - Coreset Subsampling: Uniform or k-Center greedy subsampling to compress the nominal patch memory bank by 90% (enabling sub-100ms inference on local CPU/MPS).
     - Output Artifacts: Anomaly score, binary PASS/DEFECT classification, and localized bounding polygon / heatmap overlay.
