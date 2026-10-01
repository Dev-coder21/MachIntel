#!/usr/bin/env python3
"""
CLI script to evaluate risk assessments and generate operational alerts
for all persisted predictions across the fleet.
"""
import sys
from pathlib import Path
from sqlalchemy import func, select

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.db.session import SessionLocal
from backend.app.models.machine import Machine
from backend.app.models.prediction import Prediction
from backend.app.services.alert_service import AlertService
from backend.app.services.risk_engine import RiskEngine


def main():
    print("=" * 70)
    print(" MachIntel M5 — Evaluating Fleet Risk Assessments & Operational Alerts ")
    print("=" * 70)

    db = SessionLocal()
    try:
        risk_engine = RiskEngine(db)
        alert_service = AlertService(db)

        # Get latest prediction per machine
        subquery = (
            select(
                Prediction.machine_id,
                func.max(Prediction.observation_cycle).label("max_cycle")
            )
            .group_by(Prediction.machine_id)
            .subquery()
        )

        latest_preds_stmt = (
            select(Prediction)
            .join(
                subquery,
                (Prediction.machine_id == subquery.c.machine_id) &
                (Prediction.observation_cycle == subquery.c.max_cycle)
            )
        )
        latest_preds = list(db.execute(latest_preds_stmt).scalars().all())
        print(f"Evaluating risk for {len(latest_preds)} machines with latest predictions...")

        assessments_count = 0
        alerts_count = 0

        for pred in latest_preds:
            machine = pred.machine
            if not machine:
                continue

            # Evaluate risk assessment
            assessment = risk_engine.evaluate_prediction(pred, machine, persist=True)
            assessments_count += 1

            # Process alert generation & deduplication
            alert = alert_service.process_risk_assessment(assessment, machine)
            if alert:
                alerts_count += 1

        summary = alert_service.get_alert_summary()
        print("\n" + "=" * 70)
        print(" FLEET RISK EVALUATION COMPLETED")
        print("=" * 70)
        print(f"Total Risk Assessments Generated: {assessments_count}")
        print(f"Total Alerts Triggered:          {alerts_count}")
        print(f"Alerts Summary Breakdown:        {summary}")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
