# AI Inspector — Multimodal Industrial Investigation Assistant

MachIntel Milestone M10 introduces the **AI Inspector**: a controlled, evidence-grounded industrial intelligence investigation assistant.

The AI Inspector enables reliability engineers, plant operators, and quality auditors to conduct natural-language forensic investigations over heterogeneous predictive maintenance and computer vision inspection data.

---

## Authoritative Boundaries & Prohibitions

The AI Inspector is an **investigation and decision-support assistant**, **NOT** an autonomous operator or control agent.

### Strict Prohibitions
1. **Zero Actuator Access**: The AI Inspector possesses no mechanism, integration, or permission to issue PLC, SCADA, or physical actuator commands.
2. **Zero Autonomous Equipment Mutation**: The Inspector cannot shut down machines, modify operational settings, or manipulate process setpoints.
3. **Zero Database Mutation**: All tools exposed to the AI Inspector in M10 are strictly read-only (`read_only = True`). It cannot create, update, or delete machines, telemetry, predictions, risk assessments, alerts, visual inspection runs, inspection results, evidence records, or maintenance work orders.
4. **Zero Arbitrary SQL**: The AI Inspector has no direct SQL execution capability. Tools execute predefined, parameterized repository and service calls with strict Pydantic schema validation.
5. **Zero Dynamic Filesystem Access**: The Inspector cannot read arbitrary server files or traverse directory structures (`/etc`, `.env`, source code).
6. **Strict Domain Separation**: NASA C-MAPSS turbofan data (`MACHINE_HEALTH`) and MVTec AD optical inspection data (`VISUAL_INSPECTION`) remain isolated evidence domains. The AI Inspector explicitly refutes and rejects any hallucinated or unverified cross-domain causal links.
7. **No Guaranteed Failure Claims**: The Inspector communicates strictly in analytical terms: observed risk states, estimated remaining useful life (RUL), detected anomalies, and supporting telemetry evidence. It never claims a machine "will fail at cycle X" or invents uncalibrated confidence percentages.

---

## Core Capabilities

- **Machine Health & Prognostics**:
  - Inquire into current health index (HI), remaining useful life (RUL), and risk level for any turbofan engine in the fleet.
  - Trace telemetry sensor trends and reason codes contributing to risk transitions.
  - Review open and historical alerts and their deduplication lineage.
- **Optical Surface Inspection**:
  - Inquire into defect classes, anomaly scores, and 3-sigma decision thresholds for MVTec AD metal nut inspections.
  - Inspect visual localization evidence, coreset nearest-neighbor distances, and patch heatmaps.
- **Evidence Intelligence**:
  - Retrieve verifiable evidence records, observation cycles, and cryptographic provenance digests.
  - Inspect multi-entity evidence bundles and chronological timelines.
- **Maintenance Traceability**:
  - Correlate machine health and inspection findings with persisted maintenance work orders and human review outcomes.
- **Audit & Governance**:
  - Every investigation query, tool invocation trace, latency measurement, and returned citation is persisted in the PostgreSQL `ai_investigations` table for governance review.

---

## Documentation Navigation

- [Architecture & Investigation Orchestrator](ARCHITECTURE.md)
- [Controlled Read-Only Tool Registry](TOOLS.md)
- [Grounding Policy & Citation Verification](GROUNDING_POLICY.md)
- [Security & Prompt-Injection Defense](SECURITY.md)
- [Audit Persistence & Governance](AUDIT.md)
- [Verification & Test Suite](TESTING.md)
