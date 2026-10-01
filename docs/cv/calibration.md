# Anomaly Decision Policy & Threshold Calibration

## 1. Policy Overview

- **Policy Version**: `cv-policy-v1.0.0`
- **Output Classes**: `PASS` or `DEFECT`
- **Calibration Domain**: Normal training images exclusively ($N=220$ from `train/good`)
- **Principle**: Zero-leakage calibration prior to official test split evaluation

---

## 2. Statistical Calibration Methodology

In visual inspection and non-destructive testing, defect labels are rare or absent in factory line setup. Therefore, decision boundaries must be calibrated strictly from nominal (defect-free) reference components.

### Reference Score Sampling
For each of the $K = 220$ training normal images, its reference image-level anomaly score is calculated against the coreset memory bank:
$$s_{\text{train}, k} = \max_{i} \min_{m \in \mathcal{M}} \|p_{k, i} - m\|_2, \quad k \in \{1, \dots, 220\}$$

### Normal Reference Empirical Statistics
From the resulting normal score distribution, the empirical statistics are:

| Metric | Empirical Value |
| :--- | :---: |
| **Normal Mean ($\mu$)** | **2.4895** |
| **Normal Standard Deviation ($\sigma$)** | **0.1087** |
| **Normal Minimum Score** | 2.1904 |
| **Normal Maximum Score** | 2.7692 |
| **95th Percentile ($P_{95}$)** | 2.6681 |
| **99th Percentile ($P_{99}$)** | 2.7480 |

### 3-Sigma Industrial Process Threshold
Applying the Shewhart 3-sigma process control limit:
$$\tau = \mu + 3.0 \cdot \sigma = 2.4895 + 3.0 \times (0.1087) = \mathbf{2.8155}$$

Under a Gaussian process assumption, this calibration guarantees a theoretical false positive (false alarm) rate of $\alpha < 0.27\%$ on nominal components, while positioning the threshold safely above the observed training maximum ($2.7692 < 2.8155$).

---

## 3. Decision Boundary Implementation

The calibrated threshold $\tau = 2.8155$ is frozen into the model configuration metadata (`config.json`) and persisted in the database record:

$$\text{Decision}(I) = \begin{cases} \text{DEFECT}, & \text{if } s^* \ge \tau \\ \text{PASS}, & \text{if } s^* < \tau \end{cases}$$

No test samples—neither defective nor normal—were utilized during this derivation.
