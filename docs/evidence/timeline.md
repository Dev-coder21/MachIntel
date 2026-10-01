# Evidence Timeline Specification

## 1. Timeline Ordering Rules

In industrial machine intelligence, timestamps must reflect authentic real-world events. Inventing or interpolating wall-clock event timestamps when none exist in source data is strictly prohibited in MachIntel.

---

## 2. Machine Health Timelines (C-MAPSS)

In NASA C-MAPSS FD001, engines operate over discrete, consecutive flight cycles ($t = 1, 2, \dots, N$). The dataset specifies cycle numbers but does not provide wall-clock UTC timestamps.

### Ordering Principle
- **Primary Ordering Key**: `observation_cycle ASC NULLS LAST`
- **Secondary Ordering Key**: `created_at ASC`
- **Timestamp Policy**: `observation_time` remains strictly `NULL`. The system never synthesizes fake calendar dates for historical flight cycles.

```sql
SELECT * FROM evidence_records
WHERE domain = 'MACHINE_HEALTH' AND entity_id = :machine_id
ORDER BY observation_cycle ASC NULLS LAST, created_at ASC;
```

---

## 3. Visual Inspection Timelines (MVTec AD)

In optical industrial inspection stations, physical cameras produce imagery with authentic acquisition timestamps, and inference engines record concrete processing timestamps.

### Ordering Principle
- **Primary Ordering Key**: `observation_time ASC NULLS LAST`
- **Secondary Ordering Key**: `created_at ASC`
- **Cycle Policy**: `observation_cycle` remains strictly `NULL`. Static photographic inspections do not have operational cycles.

```sql
SELECT * FROM evidence_records
WHERE domain = 'VISUAL_INSPECTION' AND entity_id = :run_id
ORDER BY observation_time ASC NULLS LAST, created_at ASC;
```
