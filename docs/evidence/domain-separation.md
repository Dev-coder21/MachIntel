# Domain Separation & Cross-Domain Validation

## 1. Domain Separation Principles

One of the foundational tenets of MachIntel is **industrial realism and scientific rigor**.

The platform rejects the temptation of marketing-driven "multimodal fusion" when no physical or temporal connection exists between datasets:
- **NASA C-MAPSS FD001** is a dataset of continuous gas turbine engine operational degradation over flight cycles.
- **MVTec AD metal_nut** is an optical computer vision benchmark consisting of static photographic captures of industrial fasteners.

These two datasets do not share a common physical asset, physical location, operational clock, or common failure mode. Combining their outputs into a single "composite health score" or claiming that an image of a metal nut represents a component of a turbofan engine would represent an unacceptable breach of domain integrity.

---

## 2. Enforcement Rules

Domain isolation is strictly enforced at multiple layers:

### 2.1 Backend Relationship Validation
Whenever an evidence relationship is inserted via `EvidenceService.create_relationship`, the service executes domain verification:
```python
if source_evidence.domain != target_evidence.domain:
    raise CrossDomainEvidenceException(
        f"Cross-domain evidence relationships are rejected: source {source_evidence.domain} "
        f"cannot relate to target {target_evidence.domain}."
    )
```
Any attempt to link a `MACHINE_HEALTH` record with a `VISUAL_INSPECTION` record results in an immediate `CrossDomainEvidenceException` (HTTP 400).

### 2.2 Prohibited Relationship Examples
The following relationships are explicitly barred:
- `C-MAPSS MACHINE` $\xrightarrow{\text{BELONGS\_TO}}$ `MVTec IMAGE`
- `C-MAPSS RUL` $\xrightarrow{\text{DERIVED\_FROM}}$ `MVTec ANOMALY_SCORE`
- `MVTec ANOMALY_SCORE` $\xrightarrow{\text{MODIFIES}}$ `C-MAPSS HEALTH_INDEX`
- `C-MAPSS ALERT` $\xrightarrow{\text{TRIGGERED\_BY}}$ `MVTec DEFECT_DECISION`

### 2.3 Evidence Bundle Separation
Evidence bundles are strictly single-domain. A bundle with `domain="MACHINE_HEALTH"` can only contain items with `domain="MACHINE_HEALTH"`. Mixing items across domains throws a validation error.

### 2.4 User Interface Segregation
- The Machine Detail page (`/machines/[id]`) contains an **Evidence Lineage** tab displaying strictly C-MAPSS FD001 causal records.
- The Visual Inspection Detail modal displays exclusively MVTec optical capture provenance, WideResNet feature memory bank stats, and benchmark ground truth masks.
- The Evidence Intelligence Workspace (`/evidence`) features a top-level **Domain Selector** that completely partitions the view between `MACHINE_HEALTH` and `VISUAL_INSPECTION`.
