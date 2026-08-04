from risktrace.db.base import Base
from risktrace.db.models import Entity, Event, EventDocument, EvidenceLink, RawDocument


def test_core_traceability_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "entities",
        "event_documents",
        "events",
        "evidence_links",
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
