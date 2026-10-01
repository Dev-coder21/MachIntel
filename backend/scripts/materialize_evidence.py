#!/usr/bin/env python3
"""
MachIntel Evidence Intelligence Materialization Script
Scans persisted M4–M7 records across NASA C-MAPSS and MVTec AD,
materializing unified, traceable evidence records, causal relationships, and bundles.
Guaranteed idempotent: running multiple times produces 0 duplicate records.
"""

import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.db.session import SessionLocal
from backend.app.services.evidence_service import EvidenceService
from backend.app.core.logging import logger


def main():
    print("================================================================================")
    print("          MACHINTEL — EVIDENCE INTELLIGENCE MATERIALIZATION (M8)                ")
    print("================================================================================")

    db = SessionLocal()
    try:
        print("\nScanning database for authoritative M4–M7 records...")
        stats = EvidenceService.materialize_all_evidence(db)

        print("\n--- Materialization Summary ---")
        print(f"Authoritative Source Records Discovered : {stats['records_discovered']}")
        print(f"Evidence Records Created                : {stats['evidence_created']}")
        print(f"Evidence Relationships Created          : {stats['relationships_created']}")
        print(f"Evidence Bundles Assembled              : {stats['bundles_created']}")
        print(f"Existing Records Skipped (Idempotent)   : {stats['skipped_existing']}")
        print(f"Unsupported Cross-Domain Links Rejected : {stats['cross_domain_rejected']}")
        if stats["errors"]:
            print(f"Errors Encountered                      : {len(stats['errors'])}")
            for err in stats["errors"]:
                print(f"  - {err}")
        else:
            print("Errors Encountered                      : 0 (Clean)")

        print("\n[SUCCESS] Evidence Intelligence materialization complete.\n")
    except Exception as e:
        logger.exception("Materialization failed with error")
        print(f"\n[FATAL ERROR] Materialization failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
