# Evidence Materialization & Idempotency

## 1. Materialization Pipeline

The script `backend/scripts/materialize_evidence.py` indexes all authoritative records created in Milestones M4, M5, M6, and M7 into the generalized evidence layer.

### Scanned Entities:
1. **Telemetry Records**: Latest cycles per C-MAPSS engine (`telemetry_records`).
2. **RUL Predictions**: Persisted model predictions (`rul_predictions`).
3. **Risk Assessments**: Evaluated operational risk states (`risk_assessments`).
4. **Active Alerts**: Operational alert records (`alerts`).
5. **Inspection Runs**: MVTec AD PatchCore inspection batches (`inspection_runs`).
6. **Inspection Results**: Individual optical test samples (`inspection_results`).

---

## 2. Idempotency Guarantees

To ensure auditability and zero duplicate proliferation, materialization enforces strict idempotency:
- Before creating any `EvidenceRecord`, the service checks for existing records with the same `(domain, entity_type, entity_id, evidence_type, source_reference)`.
- Existing records are indexed into a local cache; subsequent runs detect matches and skip insertion.
- Evidence relationships check for matching `(source_evidence_id, target_evidence_id, relationship_type)`.
- Evidence bundles check for existing `(domain, entity_type, entity_id, bundle_name)`.

### Verification Results
```bash
# Run 1 (Initial Materialization):
Authoritative Source Records Discovered : 1,096
Evidence Records Created                : 1,391
Evidence Relationships Created          : 1,158
Evidence Bundles Assembled              : 233
Existing Records Skipped                : 0
Errors Encountered                      : 0

# Run 2 (Idempotency Check):
Authoritative Source Records Discovered : 1,096
Evidence Records Created                : 0
Evidence Relationships Created          : 0
Evidence Bundles Assembled              : 0
Existing Records Skipped (Idempotent)   : 1,392
Errors Encountered                      : 0
```
Zero duplicate records are created when re-running the script.
