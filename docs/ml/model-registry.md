# Model Registry & Artifact Management

## Overview
MachIntel persists trained machine-learning model weights, scalers, and metadata locally under `storage/models/rul/<model-version>/` and tracks their operational status in the relational PostgreSQL `model_registry` table.

## Local Storage Layout
```
storage/models/rul/
├── rul-randomforest-v1.0.0/
│   ├── model.joblib          (Serialized scikit-learn RandomForestRegressor)
│   ├── scaler.joblib         (Serialized scikit-learn RobustScaler)
│   ├── metadata.json         (Hyperparameters, versions, training split, metrics)
│   └── feature_names.json    (Deterministic ordered list of 102 feature names)
└── rul-ridge-v1.0.0/
    ├── model.joblib          (Serialized scikit-learn Ridge regressor)
    ├── scaler.joblib         (Serialized scikit-learn RobustScaler)
    ├── metadata.json         (Hyperparameters, versions, training split, metrics)
    └── feature_names.json    (Deterministic ordered list of 102 feature names)
```

Binary `.joblib` model artifacts are excluded from Git via `.gitignore` (`storage/*`), preserving repository cleanliness while maintaining automated CLI reproducibility (`backend/scripts/train_models.py`).

## Database Schema: `model_registry`
```sql
CREATE TABLE model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(100) UNIQUE NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    algorithm VARCHAR(50) NOT NULL,
    task VARCHAR(50) DEFAULT 'RUL_REGRESSION' NOT NULL,
    dataset_identifier VARCHAR(50) NOT NULL,
    feature_engineering_version VARCHAR(50) DEFAULT '1.0.0' NOT NULL,
    preprocessing_version VARCHAR(50) DEFAULT '1.0.0' NOT NULL,
    window_size INTEGER DEFAULT 20 NOT NULL,
    hyperparameters JSONB NOT NULL,
    metrics JSONB NOT NULL,
    feature_names JSONB NOT NULL,
    feature_importances JSONB NOT NULL,
    artifact_path VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
CREATE INDEX ix_model_registry_is_active ON model_registry (is_active);
```

## Database Schema: `predictions`
```sql
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id UUID NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    model_version_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE RESTRICT,
    dataset_id UUID REFERENCES dataset_metadata(id) ON DELETE SET NULL,
    feature_engineering_version VARCHAR(50) DEFAULT '1.0.0' NOT NULL,
    observation_cycle INTEGER NOT NULL,
    predicted_rul DOUBLE PRECISION NOT NULL,
    health_index DOUBLE PRECISION NOT NULL,
    operational_state VARCHAR(30) DEFAULT 'NORMAL' NOT NULL,
    metadata_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
CREATE INDEX ix_predictions_machine_cycle ON predictions (machine_id, observation_cycle);
```

## In-Memory Model Caching
To maintain sub-10ms response latency on repeated predictions, `PredictionService` maintains a memory cache `_MODEL_CACHE: Dict[str, Tuple[Any, Any, List[str]]]` storing the unpickled model, scaler, and feature headers.
