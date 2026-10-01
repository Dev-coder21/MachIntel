# Feature Engineering Foundation & ML Handoff Contract

## 1. Specification & Versioning
- **Feature Engineering Version:** `1.0.0`
- **Preprocessing Version:** `1.0.0`
- **Baseline Window Size ($W$):** `20` cycles (approved in Phase 0 decision record)
- **Minimum Observations ($min\_periods$):** `1` cycle (expanding window for initial cycles)
- **Total Derived Features per Cycle:** **96 features** ($16 \text{ active channels} \times 6 \text{ representations}$)

---

## 2. Active Channel Set
Out of 21 raw sensors and 3 operational settings, exactly 16 dynamic channels exhibit informative degradation patterns in FD001:

| Channel Key | Engineering Name | Measurement Description | Unit |
| :--- | :--- | :--- | :--- |
| `op_setting_1` | Mach Number | Ambient flight velocity condition | Mach |
| `op_setting_2` | Throttle Resolver Angle | Power lever angle setting | TRA |
| `sensor_2` | LPC Outlet Temperature ($T_{24}$) | Low-pressure compressor discharge temperature | °R |
| `sensor_3` | HPC Outlet Temperature ($T_{30}$) | High-pressure compressor discharge temperature | °R |
| `sensor_4` | LPT Outlet Temperature ($T_{50}$) | Low-pressure turbine exhaust gas temperature | °R |
| `sensor_6` | Bypass Duct Pressure ($P_{2}$) | Bypass duct total pressure | psia |
| `sensor_7` | HPC Outlet Total Pressure ($P_{30}$) | High-pressure compressor delivery pressure | psia |
| `sensor_8` | Physical Fan Speed ($N_{f}$) | Fan rotational velocity | rpm |
| `sensor_9` | Physical Core Speed ($N_{c}$) | Core spool rotational velocity | rpm |
| `sensor_11` | HPC Static Pressure ($P_{s30}$) | Combustor inlet static pressure | psia |
| `sensor_12` | Fuel Flow Ratio ($\phi$) | Ratio of fuel mass flow rate to $P_{s30}$ | pps/psi |
| `sensor_13` | Corrected Fan Speed ($NR_{f}$) | Temperature-corrected fan speed | rpm |
| `sensor_14` | Corrected Core Speed ($NR_{c}$) | Temperature-corrected core speed | rpm |
| `sensor_15` | Bypass Ratio ($BPR$) | Mass ratio of bypass air to core air | — |
| `sensor_17` | Bleed Enthalpy ($htBleed$) | Bleed air specific enthalpy | — |
| `sensor_20` | HPT Coolant Bleed ($W_{31}$) | High-pressure turbine cooling airflow | lbm/s |
| `sensor_21` | LPT Coolant Bleed ($W_{32}$) | Low-pressure turbine cooling airflow | lbm/s |

### Excluded Invariant Channels ($\sigma = 0$):
`op_setting_3`, `sensor_1`, `sensor_5`, `sensor_10`, `sensor_16`, `sensor_18`, `sensor_19`.
*Requests attempting to compute rolling features on invariant channels are rejected.*

---

## 3. Mathematical Formulations

For each active channel $x$, let $x_t$ denote the measurement at cycle $t \in [1, N]$.
The trailing causal window at cycle $t$ is:
$$\mathcal{W}_t = \{ x_j \mid \max(1, t - W + 1) \le j \le t \}, \quad k_t = |\mathcal{W}_t| = \min(t, W)$$

### 1. Rolling Mean ($\mu_t$)
$$\mu_t = \frac{1}{k_t} \sum_{x \in \mathcal{W}_t} x$$

### 2. Rolling Sample Standard Deviation ($\sigma_t$)
$$\sigma_t = \begin{cases} 
0.0 & \text{if } k_t \le 1 \\
\sqrt{\frac{1}{k_t - 1} \sum_{x \in \mathcal{W}_t} (x - \mu_t)^2} & \text{if } k_t > 1
\end{cases}$$

### 3. Rolling Extrema ($x_{min, t}, x_{max, t}$)
$$x_{min, t} = \min_{x \in \mathcal{W}_t} (x), \quad x_{max, t} = \max_{x \in \mathcal{W}_t} (x)$$

### 4. Rolling OLS Linear Slope ($\beta_t$)
Fits an ordinary least squares regression line over cycles $c_j \in [\max(1, t-W+1), t]$:
$$\bar{c} = \frac{1}{k_t} \sum c_j, \quad \bar{x} = \frac{1}{k_t} \sum x_j$$
$$\beta_t = \begin{cases}
0.0 & \text{if } k_t \le 1 \text{ or } \sum (c_j - \bar{c})^2 = 0 \\
\frac{\sum_{j} (c_j - \bar{c})(x_j - \bar{x})}{\sum_{j} (c_j - \bar{c})^2} & \text{if } k_t > 1
\end{cases}$$

---

## 4. Initial Observations Behavior ($t < W$)
For cycles $1 \le t < 20$:
- Rather than discarding the first 19 observations as `NaN`, MachIntel uses an **expanding window** ($min\_periods = 1$).
- At cycle 1: $\mu_1 = x_1$, $\sigma_1 = 0.0$, $x_{min, 1} = x_1$, $x_{max, 1} = x_1$, $\beta_1 = 0.0$.
- For $2 \le t < 20$: statistics are computed over the available historical observations $1..t$.
- For $t \ge 20$: statistics are computed over the exact trailing 20 cycles.
- This guarantees zero cycle truncation and enables immediate inference on early-flight engines.

---

## 5. Milestone M4 Handoff Contract
In Milestone M4, the RUL regression model will extract features using:

```python
from backend.app.services.feature_service import FeatureExtractionService

service = FeatureExtractionService(db_session)
# Extracts 96 causal features for an engine
df = service.extract_features_df("TURBOFAN-ENG-001", start_cycle=1, end_cycle=192)
```

### Preprocessing & Scaling Rules for M4:
- Feature scalers (e.g. `RobustScaler` or `MinMaxScaler`) must be fitted **strictly on `INTERNAL_TRAIN` (Units 1–80)**.
- Fitted scalers will transform `INTERNAL_VAL` (Units 81–100) and `EVAL_TEST` (Units 1–100) without refitting.
- Target RUL clipping: piece-wise linear target capped at $RUL_{max} = 125$ cycles.
