import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import RobustScaler
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.ml.metrics import calculate_phm_score, calculate_rmse
from backend.app.ml.rul_dataset import (
    RUL_MAX_CAP,
    build_test_evaluation_matrix,
    build_training_matrix,
)
from backend.app.models.machine import Machine, SplitCategory
from backend.app.models.model_registry import ModelRegistry
from backend.app.services.feature_service import FeatureExtractionService

STORAGE_DIR = Path("storage/models/rul")


class ModelTrainer:
    def __init__(self, db: Session):
        self.db = db
        self.feature_service = FeatureExtractionService(db)
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def train_and_evaluate_all(self) -> Dict[str, Any]:
        """
        Executes end-to-end training, validation, official test evaluation, and artifact registration.
        """
        print("[M4 ML Pipeline] Step 1/6: Building dataset matrices...")
        X_train, y_train, feat_names, _ = build_training_matrix(
            self.db, SplitCategory.INTERNAL_TRAIN, self.feature_service
        )
        X_val, y_val, _, _ = build_training_matrix(
            self.db, SplitCategory.INTERNAL_VAL, self.feature_service
        )
        X_test, y_test, _, test_keys = build_test_evaluation_matrix(
            self.db, self.feature_service
        )

        print(f"  INTERNAL_TRAIN: {X_train.shape[0]} samples, {X_train.shape[1]} features")
        print(f"  INTERNAL_VAL:   {X_val.shape[0]} samples, {X_val.shape[1]} features")
        print(f"  EVAL_TEST:      {X_test.shape[0]} engines, {X_test.shape[1]} features")

        # Step 2: Fit scaler STRICTLY on training data
        print("[M4 ML Pipeline] Step 2/6: Fitting RobustScaler strictly on INTERNAL_TRAIN (Units 1-80)...")
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        X_test_scaled = scaler.transform(X_test)

        # Baseline Model 1: Ridge Regression
        print("[M4 ML Pipeline] Step 3/6: Training Baseline 1 (Ridge Regression)...")
        ridge = Ridge(alpha=100.0, random_state=42)
        ridge.fit(X_train_scaled, y_train)

        pred_val_ridge = np.maximum(0.0, ridge.predict(X_val_scaled))
        pred_test_ridge = np.maximum(0.0, ridge.predict(X_test_scaled))

        ridge_val_rmse = calculate_rmse(y_val, pred_val_ridge)
        ridge_val_phm = calculate_phm_score(y_val, pred_val_ridge)
        ridge_test_rmse = calculate_rmse(y_test, pred_test_ridge)
        ridge_test_phm = calculate_phm_score(y_test, pred_test_ridge)

        # Calculate normalized feature importances for Ridge (absolute weights)
        abs_coef = np.abs(ridge.coef_)
        norm_coef = abs_coef / (np.sum(abs_coef) + 1e-12)
        ridge_feat_imp = {feat_names[i]: round(float(norm_coef[i]), 5) for i in range(len(feat_names))}
        # Sort top 15
        ridge_top_imp = dict(sorted(ridge_feat_imp.items(), key=lambda x: x[1], reverse=True)[:15])

        ridge_metrics = {
            "val_rmse": round(ridge_val_rmse, 4),
            "val_phm_score": round(ridge_val_phm, 2),
            "test_rmse": round(ridge_test_rmse, 4),
            "test_phm_score": round(ridge_test_phm, 2),
            "train_samples": len(y_train),
            "val_samples": len(y_val),
            "test_samples": len(y_test),
        }
        print(f"  Ridge -> Val RMSE: {ridge_val_rmse:.2f}, Val PHM: {ridge_val_phm:.1f} | Test RMSE: {ridge_test_rmse:.2f}, Test PHM: {ridge_test_phm:.1f}")

        # Baseline Model 2: Random Forest Regressor
        print("[M4 ML Pipeline] Step 4/6: Training Baseline 2 (Random Forest Regressor)...")
        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1,
        )
        rf.fit(X_train_scaled, y_train)

        pred_val_rf = np.maximum(0.0, rf.predict(X_val_scaled))
        pred_test_rf = np.maximum(0.0, rf.predict(X_test_scaled))

        rf_val_rmse = calculate_rmse(y_val, pred_val_rf)
        rf_val_phm = calculate_phm_score(y_val, pred_val_rf)
        rf_test_rmse = calculate_rmse(y_test, pred_test_rf)
        rf_test_phm = calculate_phm_score(y_test, pred_test_rf)

        rf_raw_imp = rf.feature_importances_
        rf_feat_imp = {feat_names[i]: round(float(rf_raw_imp[i]), 5) for i in range(len(feat_names))}
        rf_top_imp = dict(sorted(rf_feat_imp.items(), key=lambda x: x[1], reverse=True)[:15])

        rf_metrics = {
            "val_rmse": round(rf_val_rmse, 4),
            "val_phm_score": round(rf_val_phm, 2),
            "test_rmse": round(rf_test_rmse, 4),
            "test_phm_score": round(rf_test_phm, 2),
            "train_samples": len(y_train),
            "val_samples": len(y_val),
            "test_samples": len(y_test),
        }
        print(f"  RandomForest -> Val RMSE: {rf_val_rmse:.2f}, Val PHM: {rf_val_phm:.1f} | Test RMSE: {rf_test_rmse:.2f}, Test PHM: {rf_test_phm:.1f}")

        # Step 5: Model Selection Rule
        # Rule: Model with lowest validation RMSE is selected for active serving.
        print("[M4 ML Pipeline] Step 5/6: Applying Model Selection Rule...")
        if rf_val_rmse <= ridge_val_rmse:
            selected_model_id = "rul-randomforest-v1.0.0"
            selected_algorithm = "RandomForestRegressor"
            print(f"  => Selected: RandomForest (Val RMSE {rf_val_rmse:.2f} <= Ridge Val RMSE {ridge_val_rmse:.2f})")
        else:
            selected_model_id = "rul-ridge-v1.0.0"
            selected_algorithm = "Ridge"
            print(f"  => Selected: Ridge (Val RMSE {ridge_val_rmse:.2f} < RF Val RMSE {rf_val_rmse:.2f})")

        # Step 6: Persist Artifacts and Register in Database
        print("[M4 ML Pipeline] Step 6/6: Persisting artifacts and registering models in database...")
        self._persist_model(
            model_id="rul-ridge-v1.0.0",
            model_name="C-MAPSS RUL Ridge Regressor",
            algorithm="Ridge",
            model_obj=ridge,
            scaler_obj=scaler,
            hyperparameters={"alpha": 100.0, "random_state": 42},
            metrics=ridge_metrics,
            feature_names=feat_names,
            feature_importances=ridge_top_imp,
            is_active=(selected_model_id == "rul-ridge-v1.0.0"),
        )

        self._persist_model(
            model_id="rul-randomforest-v1.0.0",
            model_name="C-MAPSS RUL Random Forest Regressor",
            algorithm="RandomForestRegressor",
            model_obj=rf,
            scaler_obj=scaler,
            hyperparameters={"n_estimators": 100, "max_depth": 12, "min_samples_split": 5, "random_state": 42},
            metrics=rf_metrics,
            feature_names=feat_names,
            feature_importances=rf_top_imp,
            is_active=(selected_model_id == "rul-randomforest-v1.0.0"),
        )

        return {
            "selected_model": selected_model_id,
            "ridge_metrics": ridge_metrics,
            "randomforest_metrics": rf_metrics,
            "training_split": "Units 1-80 (16,635 cycles)",
            "validation_split": "Units 81-100 (3,996 cycles)",
            "test_split": "Official Test Units 1-100 (100 engines)",
        }

    def _persist_model(
        self,
        model_id: str,
        model_name: str,
        algorithm: str,
        model_obj: Any,
        scaler_obj: Any,
        hyperparameters: Dict[str, Any],
        metrics: Dict[str, Any],
        feature_names: List[str],
        feature_importances: Dict[str, float],
        is_active: bool,
    ):
        model_dir = STORAGE_DIR / model_id
        model_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(model_obj, model_dir / "model.joblib")
        joblib.dump(scaler_obj, model_dir / "scaler.joblib")

        meta = {
            "model_id": model_id,
            "model_name": model_name,
            "algorithm": algorithm,
            "dataset_identifier": "NASA-C-MAPSS-FD001",
            "feature_engineering_version": "1.0.0",
            "preprocessing_version": "1.0.0",
            "window_size": 20,
            "target_rul_cap": RUL_MAX_CAP,
            "hyperparameters": hyperparameters,
            "metrics": metrics,
        }
        with open(model_dir / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2)

        with open(model_dir / "feature_names.json", "w") as f:
            json.dump(feature_names, f, indent=2)

        # Upsert in Database
        existing = self.db.execute(
            select(ModelRegistry).where(ModelRegistry.model_id == model_id)
        ).scalar_one_or_none()

        if existing:
            existing.model_name = model_name
            existing.algorithm = algorithm
            existing.hyperparameters = hyperparameters
            existing.metrics = metrics
            existing.feature_names = feature_names
            existing.feature_importances = feature_importances
            existing.artifact_path = str(model_dir)
            existing.is_active = is_active
        else:
            reg = ModelRegistry(
                model_id=model_id,
                model_name=model_name,
                algorithm=algorithm,
                task="RUL_REGRESSION",
                dataset_identifier="NASA-C-MAPSS-FD001",
                feature_engineering_version="1.0.0",
                preprocessing_version="1.0.0",
                window_size=20,
                hyperparameters=hyperparameters,
                metrics=metrics,
                feature_names=feature_names,
                feature_importances=feature_importances,
                artifact_path=str(model_dir),
                is_active=is_active,
            )
            self.db.add(reg)

        self.db.commit()
