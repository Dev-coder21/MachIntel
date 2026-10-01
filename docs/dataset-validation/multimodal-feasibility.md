# MachIntel Multimodal Feasibility & Evidence-Layer Architecture

**Document Version:** 1.0 (Phase 0 Validation Sprint)  
**Maintained By:** MachIntel Engineering Core  
**Review Standard:** Section 4.3 & Section 8 of MachIntel Master Blueprint  

---

## 1. The Multimodal Integrity Principle

Industrial AI systems deployed in mission-critical environments cannot afford deceptive engineering. A pervasive flaw in contemporary portfolio and prototype projects is **fraudulent multimodal fusion**—concatenating unrelated datasets (such as pairing a random photograph of a damaged bolt with a vibration time series from a wind turbine) and claiming the model has learned "cross-modal multimodal physics."

MachIntel rejects this practice categorically.

### The Critical Dataset Rule
> **"If Dataset A contains industrial inspection images and Dataset B contains turbofan telemetry, MachIntel must not imply that an image and telemetry row describe the same physical machine unless the data actually provides that linkage."**  
> *(MachIntel Master Blueprint, Section 4.3)*

---

## 2. Incompatibility Analysis: NASA C-MAPSS vs MVTec AD

To establish an unshakeable scientific foundation, we explicitly analyze why NASA C-MAPSS and MVTec AD cannot be fused into a single joint ML model:

| Dimension | NASA C-MAPSS (FD001) | MVTec AD (`metal_nut`) | Compatibility Assessment |
|---|---|---|---|
| **Physical Entity** | High-bypass commercial turbofan jet engine (90,000 lb thrust class). | Threaded industrial hex / flange nut fastener. | **Incompatible.** An engine is a complex dynamic thermo-mechanical assembly; a nut is an isolated passive fastener. |
| **Observation Modality** | 21 continuous thermodynamic and rotational sensor channels (temperatures, pressures, speeds). | 3-channel optical surface photography ($700 \times 700$ RGB). | **Incompatible.** One measures internal gas dynamics; the other measures external optical surface reflectance. |
| **Temporal Dynamic** | Sequential run-to-failure degradation over 100 to 360 flight cycles. | Static single-frame optical captures at a fixed instant. | **Incompatible.** C-MAPSS has strict temporal directionality; MVTec AD has zero temporal progression. |
| **Failure Mechanism** | High-Pressure Compressor (HPC) blade erosion and seal leakage. | Mechanical bending, chemical oxidation, thread stripping, surface abrasion. | **Incompatible.** The failure modes have no causal or physical overlap. |

**Engineering Verdict:** Fabricating a synthetic mapping (e.g. pretending that `metal_nut/test/scratch/004.png` depicts a bolt on `Turbofan Unit 12` at Cycle 140) would be scientifically fraudulent and violate core engineering ethics.

---

## 3. The MachIntel Evidence-Layer Architecture

Rather than forcing false model-level fusion, MachIntel solves industrial asset intelligence at the **Evidence Layer**.

In real industrial enterprises (such as aerospace manufacturing plants, power generation stations, and semiconductor fabrication facilities), asset managers monitor both **dynamic machinery telemetry** and **discrete visual inspection stations** within a unified software platform.

```
+-----------------------------------------------------------------------------------+
|                            MACHINTEL PLATFORM CORE                                |
+-----------------------------------------------------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
        v                                                                   v
+-----------------------------+                     +-----------------------------+
|    TELEMETRY VERTICAL       |                     |  VISUAL INSPECTION VERTICAL |
|  (NASA C-MAPSS Turbofans)   |                     |     (MVTec AD Fasteners)    |
|                             |                     |                             |
|  - Sensor Ingestion API     |                     |  - Image Upload API         |
|  - Time-Series Processing   |                     |  - Format / Dimension Audit |
|  - Rolling Feature Pipeline |                     |  - PatchCore Embedding Extr |
|  - RUL Regressor & HI Model |                     |  - Anomaly Score & Heatmap  |
+-----------------------------+                     +-----------------------------+
        |                                                                   |
        | TelemetryEvidence                                                 | VisualEvidence
        v                                                                   v
+-----------------------------------------------------------------------------------+
|                          UNIFIED EVIDENCE LAYER                                   |
|                                                                                   |
|  Evidence Schema:                                                                 |
|  {                                                                                |
|    evidence_id: UUID,                                                             |
|    machine_id: "TURBOFAN-ENG-012" | "AOI-LINE-04-STN-02",                          |
|    source_type: "TELEMETRY" | "VISUAL_INSPECTION",                                |
|    timestamp: ISO8601,                                                            |
|    metric: "HEALTH_INDEX" | "PREDICTED_RUL" | "DEFECT_ANOMALY_SCORE",             |
|    value: float | string,                                                         |
|    confidence: float,                                                             |
|    model_version: string,                                                         |
|    provenance: { batch_id, file_uri, sensor_channels }                            |
|  }                                                                                |
+-----------------------------------------------------------------------------------+
                                          |
                   +----------------------+----------------------+
                   |                                             |
                   v                                             v
+-------------------------------------+       +-------------------------------------+
|        EXPLAINABLE RISK ENGINE      |       |      AI INSPECTOR INVESTIGATION     |
|                                     |       |                                     |
|  - Multi-Criteria Alert Rules       |       |  - Controlled Read-Only Tool Calls  |
|  - Deterministic Reason Codes       |       |  - Strict Grounded Context Prompts  |
|  - State Lifecycle Management       |       |  - Defensible Multi-Modal Answers   |
|  - Automated Maintenance Triggers   |       |  - Verifiable Evidence Citations    |
+-------------------------------------+       +-------------------------------------+
```

---

## 4. Evidence Object Schema & Contract

Every model output and telemetry observation is wrapped into a standardized, immutable `EvidenceObject` persisted in PostgreSQL:

```python
class EvidenceObject(BaseModel):
    evidence_id: UUID
    machine_id: str
    source_type: Literal["TELEMETRY", "VISUAL_INSPECTION", "MANUAL_MAINTENANCE"]
    timestamp: datetime
    metric_name: str           # e.g., "HEALTH_INDEX", "RUL_CYCLES", "ANOMALY_SCORE"
    metric_value: float        # e.g., 0.12, 18.4, 0.88
    classification: Optional[str] = None # e.g., "CRITICAL", "DEFECT_SCRATCH"
    confidence: float          # Calibrated confidence in [0.0, 1.0]
    model_version: str         # e.g., "c-mapss-rf-rul-v1.0.0", "patchcore-metalnut-v1.0.0"
    artifact_uri: Optional[str] = None # e.g., "s3://machintel/overlays/insp_42.png"
    reason_codes: list[str]    # Deterministic explanation tags
    created_at: datetime
```

### Deterministic Risk States
The Risk Engine applies rule-based state transitions over active evidence:
1. **`NORMAL`:** $HI \ge 0.70$ and Anomaly Score $< \tau$.
2. **`WATCH`:** $0.40 \le HI < 0.70$ or single low-severity warning.
3. **`ELEVATED`:** $0.15 \le HI < 0.40$ or visual defect detected on an associated asset.
4. **`CRITICAL`:** $HI < 0.15$ or persistent severe anomaly confirmed across consecutive evaluation windows.

---

## 5. Grounded AI Inspector Interaction Pattern

The AI Inspector acts as a specialized forensic investigation assistant. It operates strictly through **controlled read-only application tools** and has no direct database write access or ungrounded generative capabilities.

When asked:
> *"Why is asset TURBOFAN-ENG-012 currently in ELEVATED status?"*

The AI Inspector:
1. Calls `get_machine(machine_id="TURBOFAN-ENG-012")`.
2. Calls `get_latest_prediction(machine_id="TURBOFAN-ENG-012")` $\rightarrow$ Returns RUL $= 22$ cycles, Health Index $= 0.176$, Model Version = `c-mapss-rf-rul-v1.0.0`.
3. Calls `get_sensor_history(machine_id="TURBOFAN-ENG-012", limit=10)` $\rightarrow$ Returns upward trend in HPC outlet temperature ($T_{30}$) and static pressure ($P_{s30}$).
4. Synthesizes an answer citing exact evidence IDs and metrics:
   > *"Asset TURBOFAN-ENG-012 is in ELEVATED status because model `c-mapss-rf-rul-v1.0.0` predicts 22 remaining operational cycles (Health Index 0.176), driven by progressive degradation in High-Pressure Compressor sensors $T_{30}$ and $P_{s30}$ over the last 15 cycles. (Evidence ID: `ev-9b12a8f4`)."*
5. If asked about visual inspection imagery for this turbofan, the AI Inspector truthfully responds:
   > *"No optical inspection records exist for this asset. TURBOFAN-ENG-012 is monitored exclusively via thermodynamic telemetry. Visual inspection is configured for optical inspection stations (e.g. AOI-LINE-04)."*

---

## 6. Criteria for True Future Multimodal Models (v2 Roadmap)

For a future version of MachIntel to deploy a true joint multi-modal neural network (e.g., Cross-Modal Attention Transformer fusing sensor signals and imagery), the candidate dataset must satisfy the **True Multimodal Triad**:
1. **Identical Machine Entity:** The sensor readings and optical images must originate from the exact same physical machine asset.
2. **Synchronized Timestamps:** Sensor frames and image acquisitions must share a synchronized wall-clock or high-precision industrial bus timestamp.
3. **Coupled Physical Dynamics:** The visual defect (e.g., surface discoloration or bearing wear scar) must be the physical consequence or cause of the observed sensor deviation (e.g., thermal spike or vibration resonance).

Candidate future datasets being monitored for this criteria include paired acoustic-thermal bearing rigs and synchronous spindle vibration/high-speed camera benchmarks.
