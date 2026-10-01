import numpy as np


def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error (RMSE)."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) == 0:
        return 0.0
    return float(np.sqrt(np.mean((y_pred - y_true) ** 2)))


def calculate_phm_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    NASA / PHM 2008 Data Challenge Asymmetric Scoring Function.
    
    Formula:
        d_i = y_pred_i - y_true_i
        s_i = exp(-d_i / 13) - 1   if d_i < 0  (Early prediction: conservative maintenance penalty)
        s_i = exp( d_i / 10) - 1   if d_i >= 0 (Late prediction: catastrophic failure penalty)
        S   = sum(s_i)
        
    Penalizes late predictions more severely than early predictions.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) == 0:
        return 0.0

    d = y_pred - y_true
    
    # Clip large positive d to avoid floating point overflow during exp
    d_clipped = np.clip(d, -300.0, 100.0)

    early_mask = d_clipped < 0
    late_mask = ~early_mask

    scores = np.zeros_like(d_clipped)
    scores[early_mask] = np.exp(-d_clipped[early_mask] / 13.0) - 1.0
    scores[late_mask] = np.exp(d_clipped[late_mask] / 10.0) - 1.0

    return float(np.sum(scores))
