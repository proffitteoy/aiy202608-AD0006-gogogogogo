import uuid
from datetime import UTC, datetime

import pytest

from risktrace.db.models import EventDocument, RawDocument
from risktrace.ingestion.pipeline import (
    LinkedEvidence,
    build_event_claim,
    document_group_key,
    hashed_embedding,
    metric_timestamp,
)

TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def raw_document(
    document_id: str,
    *,
    title: str | None,
    raw_text: str,
    published_at: datetime,
    source_type: str = "fact",
    source_level: str = "official",
    platform: str = "demo-provider",
    stream: str = "demo:deepseek-r1",
) -> RawDocument:
    return RawDocument(
        id=uuid.UUID(document_id),
        tenant_id=TENANT_ID,
        source_type=source_type,
        source_level=source_level,
        platform=platform,
        source_id=document_id,
        source_url="https://example.com/source",
        published_at=published_at,
        collected_at=published_at,
        received_at=published_at,
        replay_at=None,
        author_id_hash=None,
        title=title,
        raw_text=raw_text,
        language="zh-CN",
        engagement={},
        is_original=True,
        collection_method="historical_docx_import",
        license_scope="unknown_internal_demo_only",
        content_hash=document_id.replace("-", ""),
        raw_payload_ref="demo.docx#paragraphs=1-2",
        source_metadata={"_risktrace_ingestion": {"stream": stream}},
    )


def test_hashed_embedding_is_deterministic_and_normalized() -> None:
    first = hashed_embedding("DeepSeek R1 released")
    second = hashed_embedding("DeepSeek R1 released")

    assert first == second
    assert len(first) == 32
    assert pytest.approx(sum(value * value for value in first), rel=1e-6) == 1.0


def test_document_group_key_prefers_ingestion_stream() -> None:
    document = raw_document(
        "10000000-0000-0000-0000-000000000001",
        title="标题",
        raw_text="正文",
        published_at=datetime(2026, 8, 5, 1, 30, tzinfo=UTC),
        stream="demo:energy-transition",
    )

    assert document_group_key(document) == "demo:energy-transition"


def test_build_event_claim_falls_back_to_text_when_title_missing() -> None:
    document = raw_document(
        "20000000-0000-0000-0000-000000000001",
        title=None,
        raw_text="第一行结论\n第二行补充",
        published_at=datetime(2026, 8, 5, 1, 30, tzinfo=UTC),
    )

    claim = build_event_claim(document)

    assert claim.title == "第一行结论 第二行补充"
    assert claim.event_type == "demo:deepseek-r1"
    assert claim.subject_entity_keys == ("demo:deepseek-r1",)
    assert claim.published_at == document.published_at


def test_metric_timestamp_offsets_same_instant_documents() -> None:
    published_at = datetime(2026, 8, 5, 1, 30, tzinfo=UTC)
    first_document = raw_document(
        "30000000-0000-0000-0000-000000000001",
        title="A",
        raw_text="A",
        published_at=published_at,
    )
    second_document = raw_document(
        "40000000-0000-0000-0000-000000000001",
        title="B",
        raw_text="B",
        published_at=published_at,
    )
    linked = [
        LinkedEvidence(
            document=first_document,
            link=EventDocument(event_id=uuid.uuid4(), document_id=first_document.id),
        ),
        LinkedEvidence(
            document=second_document,
            link=EventDocument(event_id=uuid.uuid4(), document_id=second_document.id),
        ),
    ]

    assert metric_timestamp(linked, first_document.id) == published_at
    assert metric_timestamp(linked, second_document.id) == published_at.replace(
        microsecond=1
    )
