# NASA / PHM 2008 Asymmetric Scoring Function

## Mathematical Formulation
In industrial prognostics, early and late predictions carry vastly different operational costs:
- **Early Prediction ($d < 0$):** Predicting that an engine will fail sooner than it actually will causes premature maintenance. While sub-optimal, this is safe.
- **Late Prediction ($d > 0$):** Predicting that an engine has more life remaining than it actually does risks in-service failure, which is catastrophic.

To reflect this industrial reality, the official NASA PHM 2008 Data Challenge defined the asymmetric scoring metric:

$$d_i = \hat{y}_i - y_i$$

$$s_i = \begin{cases} \exp\left(-\frac{d_i}{13}\right) - 1 & \text{if } d_i < 0 \quad (\text{Early Prediction / Conservative}) \\ \exp\left(\frac{d_i}{10}\right) - 1 & \text{if } d_i \ge 0 \quad (\text{Late Prediction / Dangerous}) \end{cases}$$

$$S = \sum_{i=1}^{N} s_i$$

```
Penalty Score s_i
       ^
       |                          /
       |                         / (Late Prediction: d > 0, divisor 10)
  1.0 -+--                      /
       |        \              /
       |         \            /
  0.0 -+----------+----------+---------> Prediction Error d_i = y_pred - y_true
                 -10   0    +10
       (Early Prediction: d < 0, divisor 13)
```

## Numerical Properties
- For $d = 0$: $s = \exp(0) - 1 = 0$.
- For $d = -5$ (5 cycles early): $s = \exp(5/13) - 1 \approx 0.469$.
- For $d = +5$ (5 cycles late): $s = \exp(5/10) - 1 \approx 0.649$ (38.4% harsher penalty).
- For $d = +20$ (20 cycles late): $s = \exp(2) - 1 \approx 6.389$.

## Implementation & Numerical Safety
In `backend/app/ml/metrics.py`, input error vectors are clipped to $[-300.0, 100.0]$ prior to exponential evaluation:
```python
d = y_pred - y_true
d_clipped = np.clip(d, -300.0, 100.0)

early_mask = d_clipped < 0
late_mask = ~early_mask

scores = np.zeros_like(d_clipped)
scores[early_mask] = np.exp(-d_clipped[early_mask] / 13.0) - 1.0
scores[late_mask] = np.exp(d_clipped[late_mask] / 10.0) - 1.0
return float(np.sum(scores))
```
This prevents floating-point overflow during training or large initial error evaluation while strictly maintaining standard challenge scoring.
