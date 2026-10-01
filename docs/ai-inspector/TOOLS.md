# AI Inspector — Controlled Read-Only Tool Registry

The AI Inspector tool registry contains 15 read-only tools covering the machine health, visual inspection, evidence intelligence, and maintenance workflow domains.

All tools are strictly marked `read_only = True` and require at minimum `VIEWER` role authorization.

---

## 1. Machine Health Tools (`MACHINE_HEALTH`)

### `get_machine`
- **Description**: Retrieve machine identity, dataset, source, operational status, and metadata.
- **Input Parameters**:
  - `machine_id` (string, required): Asset identifier (e.g. `TURBOFAN-ENG-001`).
- **Output**: Machine identity, dataset name, operational status, cycles count, created timestamp.

### `get_machine_health_summary`
- **Description**: Retrieve comprehensive machine health summary including latest RUL, Health Index (HI), operational state, risk assessment, and telemetry features.
- **Input Parameters**:
  - `machine_id` (string, required): Asset identifier.
  - `cycle` (integer, optional): Specific observation cycle to inspect.
- **Output**: Latest prediction, RUL, HI, operational state, risk classification, reason codes, telemetry summary, and evidence IDs.

### `get_machine_predictions`
- **Description**: Retrieve persisted chronological RUL predictions and Health Index trajectory.
- **Input Parameters**:
  - `machine_id` (string, required): Asset identifier.
  - `limit` (integer, optional, default: 20, max: 100): Maximum records.
- **Output**: Array of predictions, observation cycles, predicted RULs, model version provenance.

### `get_machine_risk`
- **Description**: Retrieve current risk assessment, active policy version, reason codes, and recent state transitions.
- **Input Parameters**:
  - `machine_id` (string, required): Asset identifier.
  - `history_limit` (integer, optional, default: 10, max: 50): Number of transitions.
- **Output**: Current risk state (`NORMAL`, `WATCH`, `ELEVATED`, `CRITICAL`), policy version, reason codes, transition history.

---

## 2. Alert Tools (`MACHINE_HEALTH`)

### `get_machine_alerts`
- **Description**: Retrieve active and historical alerts for a specific machine asset.
- **Input Parameters**:
  - `machine_id` (string, required): Asset identifier.
  - `status` (string, optional): Filter by `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `SUPPRESSED`.
  - `limit` (integer, optional, default: 20, max: 100): Maximum records.
- **Output**: Persisted alerts, severity, status, triggers, evidence IDs, deduplication keys.

---

## 3. Evidence Intelligence Tools (`EVIDENCE_INTELLIGENCE`)

### `search_evidence`
- **Description**: Filter authoritative evidence records across domains with strict parameter validation.
- **Input Parameters**:
  - `domain` (string, optional): `MACHINE_HEALTH` or `VISUAL_INSPECTION`.
  - `entity_type` (string, optional): `MACHINE`, `PREDICTION`, `RISK_ASSESSMENT`, `ALERT`, `INSPECTION_RUN`, `INSPECTION_RESULT`.
  - `entity_id` (string, optional): Entity UUID or identifier.
  - `evidence_type` (string, optional): `TELEMETRY`, `RUL_PREDICTION`, `RISK_STATE`, `ANOMALY_SCORE`, etc.
  - `quality_state` (string, optional): `VERIFIED`, `DERIVED`, `UNVERIFIED`.
  - `observation_cycle` (integer, optional): Cycle filter.
  - `limit` (integer, optional, default: 20, max: 50): Page limit.
- **Output**: Matching evidence records, cryptographic digests, quality states.

### `get_evidence`
- **Description**: Retrieve single authoritative evidence record by primary key UUID.
- **Input Parameters**:
  - `evidence_id` (string, required): UUID of the evidence record.
- **Output**: Complete evidence record, quality state, provenance dictionary, policy versions, relations.

### `get_evidence_timeline`
- **Description**: Retrieve chronological evidence observation timeline for an entity.
- **Input Parameters**:
  - `domain` (string, required): `MACHINE_HEALTH` or `VISUAL_INSPECTION`.
  - `entity_type` (string, required): Entity type.
  - `entity_id` (string, required): Entity UUID or machine ID.
  - `limit` (integer, optional, default: 30, max: 100): Number of events.
- **Output**: Chronologically sorted evidence timeline entries with cycle/time markers.

### `get_evidence_bundle`
- **Description**: Retrieve multi-entity evidence bundle and its constituent items.
- **Input Parameters**:
  - `bundle_id` (string, required): Bundle UUID.
- **Output**: Bundle metadata, domain, primary entity, associated evidence items.

---

## 4. Visual Inspection Tools (`VISUAL_INSPECTION`)

### `get_inspection_runs`
- **Description**: Retrieve recent automated visual inspection runs for optical defect detection.
- **Input Parameters**:
  - `limit` (integer, optional, default: 10, max: 50): Maximum runs.
- **Output**: List of runs, category (`metal_nut`), total images, defect counts, 3-sigma thresholds, model versions.

### `get_inspection_run`
- **Description**: Retrieve detailed visual inspection run metadata, summary statistics, and threshold policy.
- **Input Parameters**:
  - `run_id` (string, required): Run UUID.
- **Output**: Run details, defect breakdown, AUROC metrics, threshold value.

### `get_inspection_results`
- **Description**: Retrieve individual image inspection results for an inspection run.
- **Input Parameters**:
  - `run_id` (string, required): Run UUID.
  - `decision` (string, optional): `PASS` or `DEFECT`.
  - `defect_class` (string, optional): `good`, `bent`, `color`, `flip`, `scratch`.
  - `limit` (integer, optional, default: 20, max: 100): Maximum results.
- **Output**: Array of image inspection items, scores, decisions, filenames, evidence IDs.

### `get_inspection_result`
- **Description**: Retrieve detailed result for a single visual inspection image, including anomaly score, threshold, and localization paths.
- **Input Parameters**:
  - `result_id` (string, required): Result UUID.
- **Output**: Anomaly score, threshold, PASS/DEFECT decision, ground truth label, localization overlay path, provenance.

---

## 5. Maintenance Workflow Tools (`MAINTENANCE_WORKFLOW`)

### `get_maintenance_work_orders`
- **Description**: Retrieve persisted maintenance work orders and recommendations across fleet assets.
- **Input Parameters**:
  - `machine_id` (string, optional): Filter by machine asset identifier.
  - `source_domain` (string, optional): `MACHINE_HEALTH` or `VISUAL_INSPECTION`.
  - `status` (string, optional): `OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
  - `limit` (integer, optional, default: 20, max: 50): Maximum records.
- **Output**: List of work orders, priorities, statuses, recommendations, evidence references.

### `get_maintenance_work_order`
- **Description**: Retrieve single maintenance work order including lifecycle history and resolution notes.
- **Input Parameters**:
  - `work_order_id` (string, required): Work order UUID.
- **Output**: Work order record, human review notes, lifecycle timestamps, linked evidence.
