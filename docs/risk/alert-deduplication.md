# Alert Deduplication & State Transition Tracking

## Problem Statement

When operating industrial assets continuously stream telemetry, successive inference evaluations on a degraded asset will repeatedly assess the asset in the same state (e.g. `CRITICAL` for multiple consecutive cycles). Generating a new alert on every evaluation causes alert fatigue and clutters the queue with duplicate records.

---

## Deduplication Strategy & Key Formulation

MachIntel uses a deterministic deduplication key:

$$\text{Deduplication Key} = \text{machine\_id} : \text{risk\_state} : \text{policy\_version}$$

Example:
```text
TURBOFAN-ENG-001:CRITICAL:risk-policy-v1.0.0
```

### Deterministic Rule:
Before creating an alert:
1. Formulate the deduplication key for the evaluated risk state.
2. Query the database for existing alerts where `deduplication_key` matches AND `status` is in `('OPEN', 'ACKNOWLEDGED')`.
3. **If an active alert exists**: Suppress alert creation. Return the existing alert reference. Do not duplicate.
4. **If no active alert exists** (or all previous alerts with that key are `RESOLVED`): Create a new alert with status `OPEN`.

---

## State Transition Tracking

Meaningful operational state transitions are explicitly tracked and persisted in the `risk_transitions` table:

```python
class RiskTransition(Base):
    __tablename__ = "risk_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(String(50), ForeignKey("machines.machine_id"), nullable=False)
    from_state = Column(String(20), nullable=False)
    to_state = Column(String(20), nullable=False)
    observation_cycle = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
```

Transitions are recorded when $S_{t} \ne S_{t-1}$.
Examples:
- **Degradation**: `NORMAL` $\rightarrow$ `WATCH` $\rightarrow$ `ELEVATED` $\rightarrow$ `CRITICAL`
- **Recovery / Sensor Recalibration**: `CRITICAL` $\rightarrow$ `ELEVATED` $\rightarrow$ `NORMAL`

Transition records are never fabricated; they are persisted only when real persisted risk assessments change state.
