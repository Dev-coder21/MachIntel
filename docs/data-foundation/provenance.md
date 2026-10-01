# Dataset Provenance & Split Policy

## 1. Provenance Record
Every prediction and diagnostic in MachIntel traces its lineage back to an authoritative dataset version and ingestion run.

### Ingested Dataset: NASA C-MAPSS FD001
- **Dataset Name:** `NASA C-MAPSS FD001`
- **Identifier:** `NASA-C-MAPSS-FD001`
- **Source:** NASA Prognostics Center of Excellence (PCoE)
- **Reference:** Saxena, A., Goebel, K., Simon, D., & Eklund, N. "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", International Conference on Prognostics and Health Management, 2008.
- **Source URL:** https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
- **License:** Public Domain / NASA Open Data
- **Retrieval Date:** 2026-10-01T01:30:00Z
- **Schema Version:** `1.0.0`
- **Ingestion Version:** `1.0.0`
- **Preprocessing Version:** `1.0.0`

### Authoritative File Checksums (SHA-256):
- `train_FD001.txt`:
  - Size: 3,515,356 bytes
  - SHA-256: `963b5e22825b34d8b21c69e1aeb4af3e647050eb672ee8834ba4b5d91d2de0f8`
  - Records: 20,631 cycles (Engines 1 to 100)
- `test_FD001.txt`:
  - Size: 2,228,855 bytes
  - SHA-256: `3cda7109ce17bafb5443f2ac926cfcf88154b941b8c4cf95eb55d1ddd6f52851`
  - Records: 13,096 cycles (Test Engines 1 to 100)
- `RUL_FD001.txt`:
  - Size: 429 bytes
  - SHA-256: `a19c8ec94931949d0485bdc35118206e9c81c4547b422efb9cf86f4ceddbceca`
  - Records: 100 integer ground-truth RUL values

---

## 2. Split Strategy Policy (Zero-Data-Leakage)

In strict adherence to the approved Phase 0 split strategy (`docs/dataset-validation/split-strategy.md`), MachIntel implements an **entity-preserving split**:

### Split Allocation:
1. **`INTERNAL_TRAIN` (Units 1–80):**
   - 80 run-to-failure engines
   - 16,635 operational flight cycles
   - Used exclusively for model parameter optimization and feature scalers.
2. **`INTERNAL_VAL` (Units 81–100):**
   - 20 run-to-failure engines
   - 3,996 operational flight cycles
   - Used exclusively for hyperparameter tuning, checkpoint selection, and early stopping.
3. **`EVAL_TEST` (Test Units 1–100):**
   - 100 censored engines
   - 13,096 operational flight cycles
   - Paired with ground-truth remaining life vector `RUL_FD001.txt` for final model benchmarking.

### Leakage Prevention Rules:
- **Never perform random row-level splitting.** Random row splits leak contiguous temporal sensor states across train and test sets, invalidating prognostic evaluation.
- All machine entities are tagged with `split_category` at the database level.
- Normalization statistics (min/max scalers) in Phase 3 must be fitted **only** on `INTERNAL_TRAIN` engines (1–80) and transformed on validation and test sets.
