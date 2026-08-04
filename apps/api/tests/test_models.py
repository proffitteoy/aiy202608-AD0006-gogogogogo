from risktrace.db.base import Base
from risktrace.db.models import (
    Entity,
    Event,
    EventAdmissionRecord,
    EventDocument,
    EventMetric,
    EvidenceLink,
    PlatformBaseline,
    RawDocument,
)


def test_core_traceability_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "entities",
        "event_admission_records",
        "event_documents",
        "event_metrics",
        "events",
        "evidence_links",
        "platform_baselines",
        "raw_documents",
    }


def test_raw_document_keeps_source_and_collection_provenance() -> None:
    columns = RawDocument.__table__.columns
    for required_column in (
        "source_id",
        "source_url",
        "published_at",
        "collected_at",
        "collection_method",
        "license_scope",
        "content_hash",
        "raw_payload_ref",
    ):
        assert required_column in columns

    assert Event.__table__.columns["tenant_id"].nullable is False
    assert Entity.__table__.columns["tenant_id"].nullable is False
    assert EventDocument.__table__.columns["document_id"].primary_key is True
    assert EvidenceLink.__table__.columns["tenant_id"].nullable is False


def test_event_engine_tables_keep_versions_inputs_and_tenant_scope() -> None:
    event_columns = Event.__table__.columns
    for required_column in (
        "last_seen_at",
        "centroid_embedding",
        "centroid_weight",
        "embedding_model",
        "admission_score",
        "heat_score",
        "momentum",
        "risk_score",
        "evidence_count",
    ):
        assert required_column in event_columns

    assert EventAdmissionRecord.__table__.columns["rule_version"].nullable is False
    assert EventAdmissionRecord.__table__.columns["tenant_id"].nullable is False
    assert EventMetric.__table__.columns["calculation_id"].primary_key is True
    assert EventMetric.__table__.columns["input_document_ids"].nullable is False
    assert EventMetric.__table__.columns["rule_version"].nullable is False
    assert PlatformBaseline.__table__.columns["tenant_id"].nullable is False
