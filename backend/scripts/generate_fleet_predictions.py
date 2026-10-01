#!/usr/bin/env python3
"""
CLI script to generate and persist real baseline prognostic predictions
across the fleet for dashboard & prognostics explorer.
"""
import sys
from pathlib import Path
from sqlalchemy import select

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.db.session import SessionLocal
from backend.app.models.machine import Machine
from backend.app.services.prediction_service import PredictionService


def main():
    print("=" * 70)
    print(" MachIntel M4 — Generating Fleet Prognostic Predictions ")
    print("=" * 70)

    db = SessionLocal()
    try:
        svc = PredictionService(db)
        machines = list(db.execute(select(Machine).order_by(Machine.machine_id.asc())).scalars().all())
        print(f"Generating latest predictions for {len(machines)} machines...")

        count = 0
        for m in machines:
            try:
                # Generate prediction at latest observed cycle
                pred = svc.predict_machine_health(m.machine_id, observation_cycle=m.max_cycle, persist=True)
                count += 1
                if count % 25 == 0 or count == len(machines):
                    print(f"  Processed {count}/{len(machines)} engines (latest: {m.machine_id} -> RUL: {pred.predicted_rul:.1f}, HI: {pred.health_index:.3f}, State: {pred.operational_state})")
            except Exception as e:
                print(f"  Error predicting for {m.machine_id}: {e}")

        # Also generate historical trajectory predictions for a few sample engines across early, mid, late cycles
        # so historical trend curves are available
        sample_engines = ["TURBOFAN-ENG-001", "TURBOFAN-ENG-002", "TURBOFAN-ENG-081", "TURBOFAN-ENG-101", "TURBOFAN-ENG-102"]
        print(f"\nGenerating multi-point historical trajectory for sample engines: {sample_engines}...")
        for eng_id in sample_engines:
            eng = db.execute(select(Machine).where(Machine.machine_id == eng_id)).scalar_one_or_none()
            if not eng:
                continue
            step = max(1, eng.max_cycle // 10)
            sample_cycles = list(range(1, eng.max_cycle, step))
            for c in sample_cycles:
                try:
                    svc.predict_machine_health(eng.machine_id, observation_cycle=c, persist=True)
                except Exception:
                    pass

        overview = svc.get_fleet_overview()
        print("\n" + "=" * 70)
        print(" FLEET PREDICTIONS GENERATED SUCCESSFULLY")
        print("=" * 70)
        print(f"Total Machines:              {overview['total_machines']}")
        print(f"Machines with Predictions:   {overview['machines_with_predictions']}")
        print(f"Active Model ID:             {overview['active_model_id']}")
        print(f"Active Model Algorithm:      {overview['active_model_algorithm']}")
        print(f"Average Predicted RUL:       {overview['average_predicted_rul']} cycles")
        print(f"Average Health Index:        {overview['average_health_index']}")
        print(f"State Distribution:          {overview['state_distribution']}")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
