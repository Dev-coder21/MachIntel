#!/usr/bin/env python3
"""
CLI Command to trigger idempotent ingestion of NASA C-MAPSS dataset.
Usage:
    python -m backend.scripts.ingest_cmapss --dataset FD001
"""
import argparse
import json
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.db.session import SessionLocal
from backend.app.services.ingestion_service import IngestionService


def main():
    parser = argparse.ArgumentParser(description="Ingest NASA C-MAPSS Turbofan Degradation Telemetry")
    parser.add_argument(
        "--dataset",
        type=str,
        default="FD001",
        help="Sub-dataset identifier (e.g. FD001)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/raw/cmapss/FD001")),
        help="Directory path containing raw C-MAPSS text files",
    )
    args = parser.parse_args()

    print(f"=== MachIntel Data Foundation Ingestion: {args.dataset} ===")
    print(f"Source Directory: {args.data_dir}")

    db = SessionLocal()
    try:
        service = IngestionService(db)
        stats = service.ingest_cmapss_fd001(args.data_dir)
        print("\n--- Ingestion Statistics Summary ---")
        print(json.dumps(stats, indent=2))
        print("\nIngestion completed successfully.")
    except Exception as exc:
        print(f"\nError during ingestion: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
