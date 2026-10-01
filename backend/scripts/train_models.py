#!/usr/bin/env python3
"""
CLI script to train and evaluate baseline RUL models for NASA C-MAPSS FD001.

Features:
- Splits: INTERNAL_TRAIN (Units 1-80), INTERNAL_VAL (Units 81-100), EVAL_TEST (Official Test 1-100)
- Preprocessing: RobustScaler fitted strictly on INTERNAL_TRAIN
- Models: Ridge Regression and Random Forest Regressor
- Metrics: RMSE and NASA/PHM 2008 asymmetric scoring function
- Predefined Selection Rule: Lowest validation RMSE selects active model
- Artifact persistence: storage/models/rul/<model-version>/
- Registry persistence: model_registry table in PostgreSQL
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.db.session import SessionLocal
from backend.app.ml.train import ModelTrainer


def main():
    print("=" * 70)
    print(" MachIntel M4 — RUL Regression Baseline Model Training & Evaluation ")
    print("=" * 70)

    db = SessionLocal()
    try:
        trainer = ModelTrainer(db)
        results = trainer.train_and_evaluate_all()
        print("\n" + "=" * 70)
        print(" TRAINING & EVALUATION COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"Selected Active Model: {results['selected_model']}")
        print(f"Training Split:        {results['training_split']}")
        print(f"Validation Split:      {results['validation_split']}")
        print(f"Test Split:            {results['test_split']}")
        print("\nModel Metrics Comparison:")
        print("----------------------------------------------------------------------")
        print("Algorithm         | Val RMSE | Val PHM  | Test RMSE | Test PHM")
        print("----------------------------------------------------------------------")
        ridge_m = results["ridge_metrics"]
        rf_m = results["randomforest_metrics"]
        print(f"Ridge Regression  | {ridge_m['val_rmse']:<8} | {ridge_m['val_phm_score']:<8} | {ridge_m['test_rmse']:<9} | {ridge_m['test_phm_score']:<8}")
        print(f"Random Forest     | {rf_m['val_rmse']:<8} | {rf_m['val_phm_score']:<8} | {rf_m['test_rmse']:<9} | {rf_m['test_phm_score']:<8}")
        print("----------------------------------------------------------------------")
        print(f"Artifacts saved to: storage/models/rul/")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
