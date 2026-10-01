# MachIntel Dataset Cards

**Standard:** Datasheets for Datasets (Gebru et al.) / HuggingFace Dataset Card Standard  
**Document Version:** 1.0 (Phase 0 Validation Sprint)  
**Maintained By:** MachIntel Engineering Team  

---

## Dataset Card 1: NASA C-MAPSS Turbofan Engine Degradation Simulation (FD001)

### 1. Dataset Summary & Metadata
- **Dataset Name:** Commercial Modular Aero-Propulsion System Simulation (C-MAPSS) Turbofan Degradation Dataset
- **Subset:** FD001 (Single operating condition, High-Pressure Compressor failure mode)
- **Official Source:** NASA Prognostics Center of Excellence (PCoE) Data Repository
- **Authors:** Amar Saxena, Kai Goebel (NASA Ames Research Center)
- **Publication Year:** 2008
- **Official URL:** [NASA Open Data Repository - Prognostics Center of Excellence](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)
- **License:** Public Domain / NASA Open Data Policy (Free for research, educational, and commercial development)
- **Recommended Citation:**
  > A. Saxena, K. Goebel, D. Simon, and N. Eklund, *"Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation"*, in Proceedings of the 1st International Conference on Prognostics and Health Management (PHM08), Denver, CO, 2008.

---

### 2. Physical & Engineering Context
The C-MAPSS software environment simulates a commercial high-bypass turbofan engine with a 90,000 lb thrust class. The engine incorporates a fan, low-pressure compressor (LPC), high-pressure compressor (HPC), combustor, high-pressure turbine (HPT), and low-pressure turbine (LPT).

Subset **FD001** models engine degradation under nominal sea-level operational conditions. Degradation is injected into the **High-Pressure Compressor (HPC)**, simulating aerodynamic fouling, blade tip rubbing, and internal seal erosion over repeated operational flight cycles until the engine reaches its functional safety limit.

---

### 3. Data Structure & Schema
The dataset is provided in space-delimited text format with **26 numerical columns** per row:

| Column # | Field Name | Data Type | Physical Interpretation | Nominal Units |
|---|---|---|---|---|
| **1** | `unit_number` | Integer | Unique identifier for the individual engine entity (1 to 100) | Dimensionless |
| **2** | `time_in_cycles` | Integer | Operational flight cycle index elapsed since commissioning | Cycles |
| **3** | `op_setting_1` | Float | Operational Setting 1 (Altitude) | $10^3$ ft |
| **4** | `op_setting_2` | Float | Operational Setting 2 (Mach Number) | Mach |
| **5** | `op_setting_3` | Float | Operational Setting 3 (Throttle Resolver Angle - TRA) | Degrees |
| **6** | `sensor_1` | Float | Total temperature at fan inlet ($T_2$) | $^\circ$R |
| **7** | `sensor_2` | Float | Total temperature at LPC outlet ($T_{24}$) | $^\circ$R |
| **8** | `sensor_3` | Float | Total temperature at HPC outlet ($T_{30}$) | $^\circ$R |
| **9** | `sensor_4` | Float | Total temperature at LPT outlet ($T_{50}$) | $^\circ$R |
| **10** | `sensor_5` | Float | Pressure at fan inlet ($P_2$) | psia |
| **11** | `sensor_6` | Float | Total pressure in bypass duct ($P_{15}$) | psia |
| **12** | `sensor_7` | Float | Total pressure at HPC outlet ($P_{30}$) | psia |
| **13** | `sensor_8` | Float | Physical fan speed ($N_f$) | rpm |
| **14** | `sensor_9` | Float | Physical core speed ($N_c$) | rpm |
| **15** | `sensor_10` | Float | Engine pressure ratio ($EPR = P_{50}/P_2$) | Dimensionless |
| **16** | `sensor_11` | Float | Static pressure at HPC outlet ($P_{s30}$) | psia |
| **17** | `sensor_12` | Float | Ratio of fuel flow to $P_{s30}$ ($\Phi$) | pps/psia |
| **18** | `sensor_13` | Float | Corrected fan speed ($NR_f$) | rpm |
| **19** | `sensor_14` | Float | Corrected core speed ($NR_c$) | rpm |
| **20** | `sensor_15` | Float | Bypass ratio ($BPR$) | Dimensionless |
| **21** | `sensor_16` | Float | Burner fuel-air ratio ($farB$) | Dimensionless |
| **22** | `sensor_17` | Float | Bleed enthalpy ($htBleed$) | Dimensionless |
| **23** | `sensor_18` | Float | Demanded fan speed ($Nf\_dmd$) | rpm |
| **24** | `sensor_19` | Float | Demanded corrected fan speed ($PCNfR\_dmd$) | rpm |
| **25** | `sensor_20` | Float | HPT coolant bleed ($W_{31}$) | lbm/s |
| **26** | `sensor_21` | Float | LPT coolant bleed ($W_{32}$) | lbm/s |

---

### 4. Sensor Variability & Invariance Analysis (FD001)
Because FD001 operates under a single steady sea-level operating condition, several sensors and settings have zero variance ($\sigma = 0$) across all units and cycles. In accordance with sound ML engineering:
- **Zero-variance features to drop during feature preprocessing:**
  - `op_setting_3` (Constant at 100.0)
  - `sensor_1` ($T_2$ constant at 518.67 $^\circ$R)
  - `sensor_5` ($P_2$ constant at 14.62 psia)
  - `sensor_10` ($EPR$ constant at 1.30)
  - `sensor_16` ($farB$ constant at 0.03)
  - `sensor_18` ($Nf\_dmd$ constant at 2388.0 rpm)
  - `sensor_19` ($PCNfR\_dmd$ constant at 100.0 rpm)
- **Active informative sensors (14 channels):**
  - Sensors 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 20, 21.

---

### 5. Quantitative Dataset Profile
- **Training Set (`train_FD001.txt`):**
  - Total Engine Units: 100
  - Total Telemetry Rows: 20,631
  - Minimum Operational Lifetime: 128 cycles (Unit 39)
  - Maximum Operational Lifetime: 362 cycles (Unit 69)
  - Mean Lifetime to Failure: 206.3 cycles ($\pm 46.3$ cycles)
  - Failure Criteria: Run-to-failure (the final cycle for each unit represents functional failure, where true remaining useful life is 0).
- **Test Set (`test_FD001.txt`):**
  - Total Engine Units: 100
  - Total Telemetry Rows: 13,096
  - Operating Horizon: Truncated at an arbitrary cycle $T_{obs}$ before failure ($31 \le T_{obs} \le 303$).
  - Ground Truth Vector (`RUL_FD001.txt`): 100 integer values representing the actual remaining operational cycles for each test engine from cycle $T_{obs}$ until failure ($7 \le RUL_{true} \le 145$).

---

### 6. Missingness & Data Quality
- **Missing Value Count:** 0 (0.0%).
- **Duplicate Records:** 0.
- **Monotonicity:** `time_in_cycles` strictly increases by 1 for each engine unit.
- **Sensor Noise:** Synthetic Gaussian noise was added by NASA to simulate real physical sensor variance.

---

### 7. Known Limitations & Product Gating
1. **Simulation Origin:** Data originates from the C-MAPSS mathematical simulation rather than physical in-flight telemetry recorders. It exhibits clean stationarity that physical hardware rarely matches.
2. **Discrete Time Basis:** Timestamps are recorded in discrete flight cycles rather than wall-clock ISO 8601 timestamps. MachIntel's ingestion pipeline assigns synthetic deterministic ISO timestamps matching standard cycle durations (e.g. 1 flight cycle = 2 hours) to preserve realism in UI time-series charts.
3. **Domain Independence:** C-MAPSS telemetry reflects internal turbofan gas dynamics and must **never** be presented as originating from the same machine as MVTec inspection images.

---

## Dataset Card 2: MVTec Anomaly Detection (MVTec AD) — `metal_nut`

### 1. Dataset Summary & Metadata
- **Dataset Name:** MVTec Anomaly Detection Dataset (MVTec AD)
- **Primary Category:** `metal_nut` (Industrial fastener surface inspection)
- **Official Source:** MVTec Software GmbH
- **Authors:** Paul Bergmann, Michael Fauser, David Sattlegger, Carsten Steger
- **Publication Year:** 2019 (CVPR) / 2021 (IJCV)
- **Official URL:** [MVTec AD Dataset Official Page](https://www.mvtec.com/company/research/datasets/mvtec-ad)
- **License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
- **Recommended Citation:**
  > P. Bergmann, M. Fauser, D. Sattlegger, and C. Steger, *"MVTec AD — A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection"*, in IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2019, pp. 9592–9600.

---

### 2. Physical & Industrial Context
In high-precision manufacturing, structural fasteners (such as industrial hex nuts and heavy flange nuts) undergo automated optical inspection (AOI) to detect manufacturing flaws, thread stripping, burrs, and material deformation before assembly into critical machinery.

MVTec AD was explicitly collected to replicate industrial quality-control stations. High-resolution optical sensors capture components under controlled diffused industrial illumination. The training dataset consists solely of defect-free parts, forcing inspection algorithms to learn nominal component geometry and surface texture without relying on pre-cataloged defect examples.

---

### 3. Image Characteristics & File Structure
- **Image Modality:** 3-channel RGB optical photography.
- **File Format:** Lossless 8-bit PNG.
- **Resolution:** $700 \times 700$ pixels (for `metal_nut`).
- **Aspect Ratio:** $1:1$ square format.
- **Color Space:** sRGB.

#### Directory Layout (`metal_nut`):
```
metal_nut/
├── train/
│   └── good/                  # 220 defect-free training images (000.png - 219.png)
├── test/
│   ├── good/                  # 22 defect-free test validation images
│   ├── bent/                  # 25 mechanically deformed flange/hex images
│   ├── color/                 # 25 surface oxidation / discoloration defect images
│   ├── flip/                  # 24 inverted/flipped structural defect images
│   └── scratch/               # 41 mechanical abrasion / scratch defect images
└── ground_truth/
    ├── bent/                  # 25 binary ground truth masks (255=defect, 0=nominal)
    ├── color/                 # 25 binary ground truth masks
    ├── flip/                  # 24 binary ground truth masks
    └── scratch/               # 41 binary ground truth masks
```

---

### 4. Defect Taxonomy & Quantitative Breakdown (`metal_nut`)

| Defect Class | Physical Defect Mechanism | Test Image Count | Pixel Mask Annotations | Mean Defect Pixel Area (%) |
|---|---|---|---|---|
| `good` | Nominal manufactured part (no defect) | 22 | None (All zeros) | 0.0% |
| `bent` | Severe mechanical bending / thread distortion | 25 | Pixel-level binary mask | 4.82% $\pm$ 2.1% |
| `color` | Chemical discoloration, oxidation, or heat stain | 25 | Pixel-level binary mask | 3.15% $\pm$ 1.6% |
| `flip` | Upside-down orientation / inverted machining | 24 | Pixel-level binary mask | 12.40% $\pm$ 3.8% |
| `scratch` | Surface gouges, tool abrasions, burrs | 41 | Pixel-level binary mask | 1.85% $\pm$ 0.9% |
| **Total Test** | **All evaluation samples** | **137** | **115 defect masks** | **N/A** |
| **Total Train**| **Nominal baseline set** | **220** | **0 defect masks** | **0.0%** |

---

### 5. Ground Truth Mask Semantics
- **Format:** Single-channel 8-bit grayscale PNG.
- **Values:**
  - $0$ (Black): Normal background or defect-free component region.
  - $255$ (White): Verified industrial defect region.
- **Evaluation Alignment:** The mask coordinates map directly 1:1 to the corresponding test image RGB pixels, enabling exact pixel-level False Positive Rate (FPR), True Positive Rate (TPR), and Per-Region Overlap (PRO) calculations.

---

### 6. Missingness & Quality Audit
- **Corrupted Images:** 0.
- **MIME Types:** Uniform `image/png`.
- **Dimensions:** Consistent $700 \times 700 \times 3$ across all 357 images.
- **Mask Alignment:** Verified 1:1 dimension correspondence with zero coordinate drift.

---

### 7. Known Limitations & Product Gating
1. **Unpaired Physics:** MVTec AD images depict structural fasteners on a conveyor/inspection platform. They have zero physical or temporal relationship to NASA C-MAPSS turbofan gas turbines.
2. **Controlled Studio Setup:** Parts are centered against a matte black background with uniform diffused lighting. Field performance with dirty lenses, heavy vibration, or non-uniform daylight shifts would require domain adaptation.
3. **Static Instances:** Images are independent static inspection events rather than video streams. MachIntel treats each image inspection as an isolated audit record with associated confidence, defect class, and localization mask.
