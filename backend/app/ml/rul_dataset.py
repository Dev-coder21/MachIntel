from typing import List, Tuple
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.machine import Machine, SplitCategory
from backend.app.services.feature_service import FeatureExtractionService


RUL_MAX_CAP = 125


def build_training_matrix(
    db: Session,
    split: SplitCategory,
    feature_service: FeatureExtractionService,
) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
    """
    Extracts the full feature matrix X and piecewise-linear target y for training or validation engines.
    
    Returns:
        (X, y, feature_names, machine_cycle_keys)
    """
    machines = list(
        db.execute(
            select(Machine)
            .where(Machine.split_category == split)
            .order_by(Machine.machine_id.asc())
        ).scalars().all()
    )

    X_list: List[np.ndarray] = []
    y_list: List[np.ndarray] = []
    keys_list: List[str] = []

    feature_cols = feature_service.get_feature_names()

    for m in machines:
        feat_df = feature_service.extract_features_df(m.machine_id)
        if feat_df.empty:
            continue

        cycles = feat_df["source_cycle"].to_numpy(dtype=int)
        total_fail_cycle = m.max_cycle

        # Piecewise-linear RUL target: min(125, T_fail - t)
        raw_rul = total_fail_cycle - cycles
        rul_targets = np.minimum(RUL_MAX_CAP, np.maximum(0, raw_rul)).astype(float)

        feat_values = feat_df[feature_cols].to_numpy(dtype=float)

        X_list.append(feat_values)
        y_list.append(rul_targets)
        for c in cycles:
            keys_list.append(f"{m.machine_id}_c{c}")

    if not X_list:
        return np.empty((0, len(feature_cols))), np.empty((0,)), feature_cols, []

    X = np.vstack(X_list)
    y = np.concatenate(y_list)

    return X, y, feature_cols, keys_list


def build_test_evaluation_matrix(
    db: Session,
    feature_service: FeatureExtractionService,
) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
    """
    Extracts feature vectors at the final observed cycle for all official test engines
    paired with ground truth from RUL_FD001.txt (clipped to RUL_MAX_CAP=125).
    
    Returns:
        (X_test, y_test, feature_names, test_machine_ids)
    """
    test_machines = list(
        db.execute(
            select(Machine)
            .where(Machine.split_category == SplitCategory.EVAL_TEST)
            .order_by(Machine.machine_id.asc())
        ).scalars().all()
    )

    X_list: List[np.ndarray] = []
    y_list: List[float] = []
    keys_list: List[str] = []

    feature_cols = feature_service.get_feature_names()

    for m in test_machines:
        if m.ground_truth_rul is None:
            continue

        feat_df = feature_service.extract_features_df(m.machine_id)
        if feat_df.empty:
            continue

        # Last observed cycle
        last_cycle_row = feat_df.iloc[-1]
        feat_vec = last_cycle_row[feature_cols].to_numpy(dtype=float)

        # Ground truth RUL clipped to RUL_MAX_CAP
        gt_rul = min(RUL_MAX_CAP, max(0, float(m.ground_truth_rul)))

        X_list.append(feat_vec)
        y_list.append(gt_rul)
        keys_list.append(m.machine_id)

    X_test = np.array(X_list, dtype=float)
    y_test = np.array(y_list, dtype=float)

    return X_test, y_test, feature_cols, keys_list
