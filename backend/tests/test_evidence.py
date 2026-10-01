import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.errors import CrossDomainEvidenceException
from backend.app.models.evidence import (
    EvidenceBundle,
    EvidenceRecord,
    EvidenceRelationship,
)
from backend.app.services.evidence_service import EvidenceService


def test_evidence_schema_and_creation(db):
    """Verifies EvidenceRecord creation with typed fields and provenance."""
    test_id = str(uuid.uuid4())
    record, created = EvidenceService.create_or_get_evidence(
        db=db,
        domain="MACHINE_HEALTH",
        entity_type="MACHINE",
        entity_id=test_id,
        evidence_type="RUL_PREDICTION",
        source="test_prognostic_engine",
        source_reference=f"predictions:{test_id}",
        quality_state="DERIVED",
        observation_cycle=45,
        value={"predicted_rul": 55.4, "health_index": 0.44},
        unit="cycles",
        confidence=None,  # Prohibit fake confidence
        explanation="Test prognostic explanation.",
        provenance={"model": "test_rf_v1"},
    )
    db.commit()

    assert created is True
    assert record.id is not None
    assert record.domain == "MACHINE_HEALTH"
    assert record.observation_cycle == 45
    assert record.confidence is None
    assert record.value["predicted_rul"] == 55.4


def test_evidence_idempotent_creation(db):
    """Verifies that calling create_or_get_evidence with duplicate parameters does not create duplicate rows."""
    test_id = str(uuid.uuid4())
    rec1, created1 = EvidenceService.create_or_get_evidence(
        db=db,
        domain="VISUAL_INSPECTION",
        entity_type="INSPECTION_RESULT",
        entity_id=test_id,
        evidence_type="ANOMALY_SCORE",
        source="test_patchcore",
        source_reference=f"results:{test_id}",
        quality_state="VERIFIED",
        value={"anomaly_score": 3.12},
    )
    db.commit()
    assert created1 is True

    # Call again with identical parameters
    rec2, created2 = EvidenceService.create_or_get_evidence(
        db=db,
        domain="VISUAL_INSPECTION",
        entity_type="INSPECTION_RESULT",
        entity_id=test_id,
        evidence_type="ANOMALY_SCORE",
        source="test_patchcore",
        source_reference=f"results:{test_id}",
        quality_state="VERIFIED",
        value={"anomaly_score": 3.12},
    )
    db.commit()
    assert created2 is False
    assert rec1.id == rec2.id


def test_causal_relationships_within_domain(db):
    """Verifies valid relationship creation between evidence records in the same domain."""
    ent_id = str(uuid.uuid4())
    rec1, _ = EvidenceService.create_or_get_evidence(
        db=db,
        domain="MACHINE_HEALTH",
        entity_type="MACHINE",
        entity_id=ent_id,
        evidence_type="TELEMETRY",
        source="c_mapss",
        source_reference=f"telemetry:{ent_id}:10",
        quality_state="VERIFIED",
        observation_cycle=10,
    )
    rec2, _ = EvidenceService.create_or_get_evidence(
        db=db,
        domain="MACHINE_HEALTH",
        entity_type="MACHINE",
        entity_id=ent_id,
        evidence_type="RUL_PREDICTION",
        source="rul_engine",
        source_reference=f"pred:{ent_id}:10",
        quality_state="DERIVED",
        observation_cycle=10,
    )
    db.commit()

    rel, created = EvidenceService.create_relationship(
        db=db,
        source_evidence_id=rec2.id,
        target_evidence_id=rec1.id,
        relationship_type="DERIVED_FROM",
        relationship_metadata={"algorithm": "random_forest"},
    )
    db.commit()

    assert created is True
    assert rel.relationship_type == "DERIVED_FROM"


def test_unsupported_cross_domain_relationship_rejected(db):
    """
    CRITICAL QUALITY GATE:
    Verifies that linking MACHINE_HEALTH evidence with VISUAL_INSPECTION evidence is rejected.
    Enforces strict prohibition of unsupported cross-modal fusion.
    """
    mach_id = str(uuid.uuid4())
    insp_id = str(uuid.uuid4())

    mach_evidence, _ = EvidenceService.create_or_get_evidence(
        db=db,
        domain="MACHINE_HEALTH",
        entity_type="MACHINE",
        entity_id=mach_id,
        evidence_type="RUL_PREDICTION",
        source="c_mapss_model",
        source_reference=f"pred:{mach_id}",
        quality_state="DERIVED",
        observation_cycle=80,
    )

    cv_evidence, _ = EvidenceService.create_or_get_evidence(
        db=db,
        domain="VISUAL_INSPECTION",
        entity_type="INSPECTION_RESULT",
        entity_id=insp_id,
        evidence_type="ANOMALY_SCORE",
        source="patchcore",
        source_reference=f"insp:{insp_id}",
        quality_state="VERIFIED",
    )
    db.commit()

    with pytest.raises(CrossDomainEvidenceException) as exc_info:
        EvidenceService.create_relationship(
            db=db,
            source_evidence_id=mach_evidence.id,
            target_evidence_id=cv_evidence.id,
            relationship_type="DERIVED_FROM",
        )

    assert "Unsupported cross-domain relationship rejected" in str(exc_info.value)
    assert "MACHINE_HEALTH" in str(exc_info.value)
    assert "VISUAL_INSPECTION" in str(exc_info.value)


def test_bundle_creation_and_domain_isolation(db):
    """Verifies EvidenceBundle groups only domain-congruent evidence."""
    ent_id = str(uuid.uuid4())
    e1, _ = EvidenceService.create_or_get_evidence(
        db=db,
        domain="VISUAL_INSPECTION",
        entity_type="INSPECTION_RUN",
        entity_id=ent_id,
        evidence_type="DATASET_PROVENANCE",
        source="mvtec_run",
        source_reference=f"run:{ent_id}",
        quality_state="PROVENANCE_ONLY",
    )
    e2, _ = EvidenceService.create_or_get_evidence(
        db=db,
        domain="VISUAL_INSPECTION",
        entity_type="INSPECTION_RUN",
        entity_id=ent_id,
        evidence_type="ANALYTICS",
        source="analytics",
        source_reference=f"analytics:{ent_id}",
        quality_state="DERIVED",
    )
    db.commit()

    bundle = EvidenceService.create_bundle(
        db=db,
        bundle_name=f"Test Bundle {ent_id[:8]}",
        domain="VISUAL_INSPECTION",
        entity_type="INSPECTION_RUN",
        entity_id=ent_id,
        evidence_items=[(e1.id, "PROVENANCE", 1), (e2.id, "PRIMARY_OBSERVATION", 2)],
    )
    db.commit()

    assert bundle.id is not None
    assert len(bundle.items) == 2
    assert bundle.domain == "VISUAL_INSPECTION"

    # Verify adding a cross-domain evidence record to this bundle is rejected
    mach_ev, _ = EvidenceService.create_or_get_evidence(
        db=db,
        domain="MACHINE_HEALTH",
        entity_type="MACHINE",
        entity_id="test-mach",
        evidence_type="TELEMETRY",
        source="c_mapss",
        source_reference="telemetry:test",
        quality_state="VERIFIED",
    )
    db.commit()

    with pytest.raises(CrossDomainEvidenceException):
        EvidenceService.create_bundle(
            db=db,
            bundle_name="Illegal Cross-Domain Bundle",
            domain="VISUAL_INSPECTION",
            entity_type="INSPECTION_RUN",
            entity_id=ent_id,
            evidence_items=[(mach_ev.id, "PRIMARY_OBSERVATION", 1)],
        )


def test_timeline_ordering_and_cycle_handling(db):
    """Verifies that machine health timeline respects observation_cycle sorting."""
    mach_id = f"machine-{uuid.uuid4()}"

    # Insert out-of-order cycles
    for cycle in [15, 5, 25]:
        EvidenceService.create_or_get_evidence(
            db=db,
            domain="MACHINE_HEALTH",
            entity_type="MACHINE",
            entity_id=mach_id,
            evidence_type="TELEMETRY",
            source="cmapss",
            source_reference=f"cycle:{cycle}",
            quality_state="VERIFIED",
            observation_cycle=cycle,
        )
    db.commit()

    timeline = EvidenceService.get_entity_timeline(db, "MACHINE", mach_id)
    cycles = [item.observation_cycle for item in timeline]
    assert cycles == [5, 15, 25], "Timeline must be ordered ascending by cycle."


def test_evidence_quality_states_and_no_fake_confidence(db):
    """Verifies that evidence quality states are properly recorded and confidence is not fabricated."""
    rec, _ = EvidenceService.create_or_get_evidence(
        db=db,
        domain="VISUAL_INSPECTION",
        entity_type="INSPECTION_RESULT",
        entity_id=str(uuid.uuid4()),
        evidence_type="GROUND_TRUTH",
        source="mvtec_ground_truth",
        source_reference=f"mask:{uuid.uuid4()}",
        quality_state="BENCHMARK_GROUND_TRUTH",
        value={"label": "DEFECT", "mask": True},
    )
    db.commit()

    assert rec.quality_state == "BENCHMARK_GROUND_TRUTH"
    assert rec.confidence is None


def test_api_search_evidence_filtering(client: TestClient, viewer_token_headers):
    """Verifies GET /api/v1/evidence filtering by domain and pagination."""
    resp = client.get(
        "/api/v1/evidence?domain=MACHINE_HEALTH&limit=10",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "records" in data
    assert data["domain"] == "MACHINE_HEALTH"
    for r in data["records"]:
        assert r["domain"] == "MACHINE_HEALTH"


def test_api_search_visual_inspection_evidence(client: TestClient, viewer_token_headers):
    """Verifies GET /api/v1/evidence for VISUAL_INSPECTION domain."""
    resp = client.get(
        "/api/v1/evidence?domain=VISUAL_INSPECTION&limit=10",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "records" in data
    for r in data["records"]:
        assert r["domain"] == "VISUAL_INSPECTION"


def test_api_get_evidence_by_id(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/evidence/{evidence_id}."""
    rec = db.query(EvidenceRecord).first()
    assert rec is not None

    resp = client.get(
        f"/api/v1/evidence/{rec.id}",
        headers=viewer_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(rec.id)
    assert data["domain"] == rec.domain
    assert data["evidence_type"] == rec.evidence_type


def test_api_get_bundles_and_bundle_timeline(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/evidence/bundles and /bundles/{id}/timeline."""
    bundle = db.query(EvidenceBundle).first()
    assert bundle is not None

    # List bundles
    resp = client.get("/api/v1/evidence/bundles", headers=viewer_token_headers)
    assert resp.status_code == 200
    bundles = resp.json()
    assert len(bundles) > 0

    # Get single bundle
    resp_single = client.get(f"/api/v1/evidence/bundles/{bundle.id}", headers=viewer_token_headers)
    assert resp_single.status_code == 200
    bundle_data = resp_single.json()
    assert bundle_data["id"] == str(bundle.id)
    assert len(bundle_data["items"]) > 0

    # Get bundle timeline
    resp_tl = client.get(f"/api/v1/evidence/bundles/{bundle.id}/timeline", headers=viewer_token_headers)
    assert resp_tl.status_code == 200
    tl_data = resp_tl.json()
    assert isinstance(tl_data, list)


def test_api_get_relationships_and_provenance(client: TestClient, viewer_token_headers, db):
    """Verifies GET /api/v1/evidence/relationships/{id} and /provenance/{id}."""
    rel = db.query(EvidenceRelationship).first()
    assert rel is not None

    # Get relationships
    resp_rel = client.get(
        f"/api/v1/evidence/relationships/{rel.source_evidence_id}",
        headers=viewer_token_headers,
    )
    assert resp_rel.status_code == 200
    rel_data = resp_rel.json()
    assert "outgoing" in rel_data
    assert "incoming" in rel_data

    # Get provenance
    resp_prov = client.get(
        f"/api/v1/evidence/provenance/{rel.source_evidence_id}",
        headers=viewer_token_headers,
    )
    assert resp_prov.status_code == 200
    prov_data = resp_prov.json()
    assert "provenance" in prov_data
    assert prov_data["evidence_id"] == str(rel.source_evidence_id)


def test_api_invalid_evidence_id_returns_404(client: TestClient, viewer_token_headers):
    """Verifies that querying a non-existent evidence UUID returns 404."""
    random_uuid = uuid.uuid4()
    resp = client.get(f"/api/v1/evidence/{random_uuid}", headers=viewer_token_headers)
    assert resp.status_code == 404


def test_api_unauthenticated_evidence_returns_401(client: TestClient):
    """Verifies that evidence endpoints require JWT authentication."""
    resp = client.get("/api/v1/evidence")
    assert resp.status_code == 401
