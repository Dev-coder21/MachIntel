# Machine Analytics Architecture

## 1. Architectural Scope & Boundary
Milestone M3 establishes the machine analytics and temporal feature extraction infrastructure for MachIntel. Operating strictly on real C-MAPSS FD001 telemetry persisted in PostgreSQL, this layer transforms raw sensor signals into explainable, causal rolling statistics.

In compliance with MachIntel core architectural principles:
- **Zero Prediction Fabrication:** No RUL models, health indices, risk scores, or predictive alerts are synthesized in this milestone.
- **Traceable Computation:** Every metric traces directly to an authoritative engine entity, cycle range, and mathematical transformation.
- **Non-destructive Processing:** Raw telemetry in `telemetry_records` is never overwritten, modified, or normalized in place.

---

## 2. System Architecture & Component Interaction

```
+------------------------------------------------------------------------------------+
|                         CLIENT LAYER (Next.js / React)                             |
|    - Asset Telemetry Studio: Dual Overlay (Raw + Rolling Mean + Std Envelope)      |
|    - Sensor Statistics Matrix (Min, Max, Mean, Drift Delta, % Change)              |
|    - Bivariate Correlation Heatmap (Pearson r)                                     |
|    - ML Feature Preview (96-dimensional causal vectors with contract disclaimer)   |
|    - Multi-Asset Analytical Comparison (Drift & Thermal Volatility)                |
+------------------------------------------------------------------------------------+
                                         | REST / HTTPS (JSON)
                                         v
+------------------------------------------------------------------------------------+
|                      FASTAPI ANALYTICS API ROUTER                                  |
|  - GET /machines/{id}/analytics/summary                                            |
|  - GET /machines/{id}/analytics/sensors                                            |
|  - GET /machines/{id}/analytics/trends                                             |
|  - GET /machines/{id}/analytics/correlation                                        |
|  - GET /machines/{id}/analytics/features                                           |
|  - GET /machines/analytics/overview                                                |
|  - GET /machines/analytics/compare                                                 |
+------------------------------------------------------------------------------------+
                                         |
                                         v
+------------------------------------------------------------------------------------+
|                       MACHINE ANALYTICS SERVICE                                    |
|  - Active Channel Filtering (15 informative sensors + 2 dynamic op settings)       |
|  - Invariant Channel Rejection (op_setting_3, sensors 1, 5, 10, 16, 18, 19)        |
|  - RollingFeatureCalculator: Mean, Std (ddof=1), Min, Max, OLS Linear Slope        |
|  - Uniform Decimation / Downsampling for Sub-second Visualization                 |
+------------------------------------------------------------------------------------+
                                         |
                                         v
+------------------------------------------------------------------------------------+
|                     POSTGRESQL 16 PERSISTENCE ENGINE                               |
|  - Indexed queries: (machine_id, source_cycle ASC)                                 |
|  - Zero table desynchronization via On-Demand Causal Computation                   |
+------------------------------------------------------------------------------------+
```

---

## 3. Storage Strategy: On-Demand vs. Persisted
We evaluated whether derived rolling features should be persisted into dedicated database tables or computed on demand.

### Decision: **On-Demand Vectorized Computation**
- **Cycle Volume:** In C-MAPSS FD001, individual engine trajectories range from 31 to 362 cycles.
- **Latency:** Using vectorized NumPy/Pandas slices, extracting all 96 derived features for 362 cycles executes in **< 8 ms** on modern hardware.
- **Elimination of Schema Desynchronization:** Avoids duplicating 33,727 rows $\times$ 96 columns (~3.2 million floats) in PostgreSQL.
- **Mathematical Immutability:** Eliminates the risk of stale derived features if window hyperparameters ($W$) are adjusted.
- **Formal Handoff:** The `FeatureExtractionService` provides the single source of truth for Milestone M4 model training pipelines.
