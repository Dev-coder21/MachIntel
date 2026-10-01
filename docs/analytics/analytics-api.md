# Machine Analytics API Reference

## 1. Overview
The Machine Analytics API endpoints provide bounded, authenticated access to operational sensor statistics, rolling window trends, bivariate correlation matrices, and derived ML features.

All endpoints require a valid JWT Bearer token and are mounted under `/api/v1`.

---

## 2. Endpoints

### 1. `GET /api/v1/machines/{machine_id}/analytics/summary`
Retrieves machine operational cycle coverage, sensor statistics summary, and top drifting channels.

- **Path Parameters:**
  - `machine_id` (string): Machine asset identifier (e.g. `TURBOFAN-ENG-001`) or UUID.
- **Response Model:** `MachineAnalyticsSummary`
- **Example Response:**
  ```json
  {
    "machine_id": "TURBOFAN-ENG-001",
    "machine_name": "C-MAPSS Turbofan Engine #1",
    "source_dataset": "NASA C-MAPSS (FD001)",
    "source_entity_id": "1",
    "split_category": "INTERNAL_TRAIN",
    "status": "OPERATIONAL",
    "first_cycle": 1,
    "latest_cycle": 192,
    "total_cycles": 192,
    "active_sensor_count": 15,
    "invariant_sensor_count": 7,
    "top_drifting_sensors": [ ... ],
    "sensors": [ ... ]
  }
  ```

---

### 2. `GET /api/v1/machines/{machine_id}/analytics/sensors`
Retrieves statistical profiles across all 16 active dynamic channels.

- **Response Model:** `List[SensorSummaryItem]`
- **Fields per item:** `sensor_key`, `channel_name`, `engineering_unit`, `min_value`, `max_value`, `mean_value`, `std_value`, `initial_value`, `latest_value`, `net_change`, `pct_change`, `direction`.

---

### 3. `GET /api/v1/machines/{machine_id}/analytics/trends`
Computes rolling window statistics along the operational cycle progression for a specific active channel.

- **Query Parameters:**
  - `sensor` (string, required): Active channel key (e.g. `sensor_2`, `sensor_3`, `sensor_7`). *Invariant channels are rejected with 422.*
  - `window` (integer, default: 20): Rolling window length ($2 \le W \le 100$).
  - `max_points` (integer, default: 300): Maximum points returned (decimated uniformly if cycles > max_points, preserving cycle 1 and final cycle).
- **Response Model:** `SensorTrendResponse`
- **Points Fields:** `cycle`, `raw_value`, `rolling_mean`, `rolling_std`, `rolling_min`, `rolling_max`, `rolling_slope`.

---

### 4. `GET /api/v1/machines/{machine_id}/analytics/correlation`
Computes bivariate Pearson correlation matrix between active sensor channels for an asset.

- **Query Parameters:**
  - `channels` (list of strings, optional): Subset of active channel keys.
- **Response Model:** `CorrelationMatrixResponse`
- **Fields:** `channels`, `channel_names`, `matrix` (2D float matrix with values bounded $[-1.0, 1.0]$).

---

### 5. `GET /api/v1/machines/{machine_id}/analytics/features`
Returns derived 96-dimensional causal feature vectors for downstream ML modeling.

- **Query Parameters:**
  - `start_cycle` (integer, default: 1)
  - `end_cycle` (integer, default: 50)
  - `window` (integer, default: 20)
- **Response Model:** `FeaturePreviewResponse`
- **Fields:** `feature_engineering_version`, `window_size`, `min_periods`, `scaling_policy`, `total_feature_count`, `columns`, `rows`, `disclaimer`.

---

### 6. `GET /api/v1/machines/analytics/overview`
Provides fleet-wide cycle statistics, distribution buckets, and split breakdowns.

- **Response Model:** `FleetAnalyticsOverviewResponse`

---

### 7. `GET /api/v1/machines/analytics/compare`
Performs analytical comparison across multiple assets.

- **Query Parameters:**
  - `machine_ids` (string, required): Comma-separated asset identifiers (e.g. `TURBOFAN-ENG-001,TURBOFAN-ENG-002`).
- **Response Model:** `MachineComparisonResponse`
