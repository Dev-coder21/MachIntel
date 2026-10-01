# Maintenance Recommendation & Priority Policy

Version: `maintenance-policy-v1.0.0`

## 1. Grounding & Rationale

MachIntel does not synthesize repair instructions or invent physical tasks unsupported by dataset ground truth. Recommendations are formulated as operational decision support guidelines derived deterministically from analytical findings.

---

## 2. Policy Mapping: Machine Health Intelligence (C-MAPSS FD001)

Recommendations are derived from evaluated `RiskAssessment` records.

| Analytical Risk State | Work Order Generated? | Priority | Deterministic Recommended Action |
|---|---|---|---|
| **NORMAL** | **NO** (Rejected with 400 Bad Request) | None | Asset operates within baseline limits. No work order is generated. |
| **WATCH** | YES | **LOW** | *"Review recent machine-health trend and schedule routine check according to site maintenance procedures."* |
| **ELEVATED** | YES | **HIGH** | *"Review recent machine-health evidence and schedule inspection according to site maintenance procedures."* |
| **CRITICAL** | YES | **CRITICAL** | *"Prioritize human review of the machine-health evidence and assess whether maintenance action is required."* |

### Reason Formulation (Machine Health)
Derived directly from the asset telemetry and regression predictions:
$$\text{Reason} = \text{"Machine } \langle\text{ID}\rangle \text{ exhibits } \langle\text{State}\rangle \text{ risk with estimated RUL of } \langle\text{RUL}\rangle \text{ cycles and Health Index } \langle\text{HI}\rangle \text{. Reason codes: } \langle\text{Codes}\rangle\text{."}$$

---

## 3. Policy Mapping: Visual Inspection Intelligence (MVTec AD metal_nut)

Recommendations are derived from evaluated `InspectionResult` records.

| Inspection Decision | Work Order Generated? | Priority | Deterministic Recommended Action |
|---|---|---|---|
| **PASS** | **NO** (Rejected with 400 Bad Request) | None | Component conforms to reference visual standards. No recommendation created. |
| **DEFECT** | YES | **HIGH** | *"Review the inspection image, anomaly localization, and benchmark/model evidence before determining the appropriate maintenance or inspection action."* |

> [!NOTE]
> **Safety Notice:** Per policy guidelines, MachIntel does NOT infer safety-critical priority solely from a benchmark defect class. Defect categories (`scratch`, `bent`, `color`, `flip`) trigger `HIGH` operational review, requiring operator confirmation.

### Reason Formulation (Visual Inspection)
$$\text{Reason} = \text{"Industrial vision pipeline detected defect class '} \langle\text{class}\rangle \text{' with anomaly score } \langle\text{score}\rangle \text{ (threshold: } \langle\tau\rangle \text{). Component inspection failed quality criteria."}$$

---

## 4. Deterministic Deduplication Policy

To prevent alert fatigue and duplicate work orders for the same incident:
- Every recommendation constructs a unique deduplication key:
  $$\text{deduplication\_key} = \langle\text{source\_type}\rangle : \langle\text{source\_reference}\rangle : \langle\text{policy\_version}\rangle$$
- **Deduplication Check:** If an active work order (`OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`) already exists with matching `deduplication_key`, the system **suppresses duplicate insertion** and returns the existing work order reference.
- **Future Distinct Events:** Distinct future assessments or subsequent defect images possess distinct source UUIDs and will cleanly trigger independent work orders.
