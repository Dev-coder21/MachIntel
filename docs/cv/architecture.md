# Computer Vision Pipeline Architecture & Domain Separation

## 1. Domain Separation Principle

MachIntel explicitly maintains clean architectural separation between its two foundational datasets:

```
+-------------------------------------------------------------------+
|                            MACHINTEL                              |
+---------------------------------+---------------------------------+
|   MACHINE HEALTH INTELLIGENCE   |  VISUAL INSPECTION INTELLIGENCE |
|  (Prognostics & Diagnostics)    |  (Optical Quality Control)      |
+---------------------------------+---------------------------------+
| • NASA C-MAPSS (FD001)          | • MVTec AD (metal_nut)          |
| • Run-to-failure run telemetry  | • High-res surface inspection   |
| • RUL regression & Health Index | • Frozen PatchCore detector     |
| • Deterministic Alert lifecycle | • Image anomaly score & heatmap |
| • Serial: TURBOFAN-ENG-XXX      | • Run/Batch: Fastener Inspection|
+---------------------------------+---------------------------------+
```

> **Critical Rule**: C-MAPSS turbofan engines and MVTec metal nuts share NO physical identity or temporal coupling. Visual inspection results are tracked independently under `inspection_runs` and `inspection_results`, preventing false multimodal claims.

---

## 2. End-to-End Visual Inspection Workflow

```mermaid
flowchart TD
    subgraph Data Layer
        A["MVTec AD metal_nut\nRaw PNGs (700x700)"]
        B["train/good (220 imgs)"]
        C["test/* (115 imgs)"]
        A --> B
        A --> C
    end

    subgraph Feature Extraction & Memory Bank
        B --> D["Frozen WideResNet-50-2\n(layer2 + layer3)"]
        D --> E["Combined Patch Embeddings\n(172,480 patches x 1536d)"]
        E --> F["Deterministic Coreset Subsampling\n(5% = 8,624 patch vectors)"]
        F --> G[("Normal Memory Bank\nstorage/models/cv/...")]
    end

    subgraph Calibration
        G --> H["Normal Reference Scoring\n(220 train images)"]
        H --> I["Calibrated Threshold tau\nmu + 3*sigma = 2.8155"]
    end

    subgraph Inference & Localization
        C --> J["Test Image Preprocessing\n(Resize 224x224, Norm)"]
        J --> K["Feature Extraction\n(784 patches x 1536d)"]
        K & G --> L["Euclidean Nearest Neighbor\nmin ||p - m||_2"]
        L --> M["Image Anomaly Score s*\n(max patch distance)"]
        L --> N["Spatial Distance Grid (28x28)\nBilinear Upsample -> 224x224"]
        N --> O["Gaussian Filter (sigma=4.0)\nNormalized Heatmap"]
        M & I --> P{"s* >= tau ?"}
        P -->|Yes| Q["DEFECT"]
        P -->|No| R["PASS"]
    end

    subgraph Persistence & API
        Q & R --> S[("PostgreSQL\ninspection_runs\ninspection_results")]
        O --> T[("Local Storage\nstorage/inspections/{run_id}/\nheatmaps/ & overlays/")]
        S & T --> U["FastAPI REST Endpoints\nRBAC + Safe Path Streaming"]
        U --> V["Next.js Industrial Inspection Station\nResults Grid, Multi-view Modal"]
    end
```

---

## 3. Storage Hierarchy & Artifact Segregation

- **Database (PostgreSQL)**:
  - `inspection_runs`: Tracks run ID, dataset identifier, category, model version, feature configuration version, policy version, calibrated threshold, total/passed/defect counts, and summary evaluation metrics JSON.
  - `inspection_results`: Stores individual image evaluation records, source filename, image-level score, model decision (`PASS`/`DEFECT`), benchmark ground truth (`PASS`/`DEFECT`), and local relative artifact paths.
- **Local Filesystem Object Storage**:
  - `storage/models/cv/mvtec-patchcore-metalnut-v1.0.0/`: Persists memory bank tensor (`memory_bank.pt`) and configuration metadata (`config.json`).
  - `storage/inspections/{run_id}/`: Stores generated colormapped anomaly heatmaps, visual overlays, and evaluation summary JSON.
