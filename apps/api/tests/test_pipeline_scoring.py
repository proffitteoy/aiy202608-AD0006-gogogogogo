import uuid
from collections import Counter
from datetime import UTC, datetime

import pytest

from risktrace.agents.pipeline import (
    SCORING_SYNTHETIC_VERSION,
    synthesize_raw_score,
    synthetic_metric_calculation_id,
)
from risktrace.db.models import EventDocument, RawDocument
from risktrace.ingestion.pipeline import LinkedEvidence, build_score_update
from risktrace.scoring.schemas import EvidenceWeightComponents, ScoreEvidenceUpdate

EVENT_ID = uuid.UUID("e1000000-0000-0000-0000-000000000001")
TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _update(
    doc_id: str,
    observation: float,
    *,
    source_reliability: float = 0.8,
    independence: float = 0.6,
    score_relevance: float = 0.8,
    freshness: float = 0.7,
    data_quality: float = 0.75,
) -> ScoreEvidenceUpdate:
    return ScoreEvidenceUpdate(
        document_id=uuid.UUID(doc_id),
        observation=observation,
        weight=EvidenceWeightComponents(
            source_reliability=source_reliability,
            independence=independence,
            score_relevance=score_relevance,
            freshness=freshness,
            data_quality=data_quality,
        ),
    )


def test_synthesize_raw_score_is_information_weighted_average() -> None:
    updates = [
        _update("10000000-0000-0000-0000-000000000001", observation=0.9),
        _update("20000000-0000-0000-0000-000000000001", observation=0.3),
    ]
    total_iw = sum(u.information_weight for u in updates)
    expected = sum(u.observation * u.information_weight for u in updates) / total_iw

    result = synthesize_raw_score(updates)

    assert pytest.approx(result, rel=1e-9) == expected
    assert 0.3 < result < 0.9


def test_synthesize_raw_score_falls_back_when_no_weight() -> None:
    # 所有权重维度为 0 → information_weight = 0
    zero_weight_update = ScoreEvidenceUpdate(
        document_id=uuid.UUID("30000000-0000-0000-0000-000000000001"),
        observation=0.42,
        weight=EvidenceWeightComponents(
            source_reliability=0.0,
            independence=0.0,
            score_relevance=0.0,
            freshness=0.0,
            data_quality=0.0,
        ),
    )
    assert synthesize_raw_score([zero_weight_update]) == 0.5
    assert synthesize_raw_score([]) == 0.5


def test_synthetic_metric_calculation_id_is_stable_and_order_insensitive() -> None:
    doc_ids = [
        "10000000-0000-0000-0000-000000000001",
        "20000000-0000-0000-0000-000000000001",
    ]
    first = synthetic_metric_calculation_id(EVENT_ID, doc_ids)
    second = synthetic_metric_calculation_id(EVENT_ID, list(reversed(doc_ids)))
    third = synthetic_metric_calculation_id(
        uuid.UUID("f0000000-0000-0000-0000-000000000001"),
        doc_ids,
    )

    assert first == second
    assert first != third
    assert isinstance(first, uuid.UUID)


def _raw_document(document_id: str, *, source_type: str, platform: str) -> RawDocument:
    return RawDocument(
        id=uuid.UUID(document_id),
        tenant_id=TENANT_ID,
        source_type=source_type,
        source_level="official" if source_type == "fact" else "authoritative",
        platform=platform,
        source_id=document_id,
        source_url="https://example.com",
        published_at=datetime(2026, 8, 5, 1, 0, tzinfo=UTC),
        collected_at=datetime(2026, 8, 5, 1, 5, tzinfo=UTC),
        received_at=datetime(2026, 8, 5, 1, 5, tzinfo=UTC),
        replay_at=None,
        author_id_hash=None,
        title="示例",
        raw_text="示例正文",
        language="zh-CN",
        engagement={},
        is_original=True,
        collection_method="historical_docx_import",
        license_scope="unknown_internal_demo_only",
        content_hash=document_id.replace("-", ""),
        raw_payload_ref="demo",
        source_metadata={},
    )


def test_synthetic_raw_score_matches_build_score_update_weights() -> None:
    """合成路径应该与 ingestion 的 build_score_update 兼容，产出可以直接喂给 CalibrationEngine。"""
    docs = [
        _raw_document(
            "10000000-0000-0000-0000-000000000001",
            source_type="fact",
            platform="disclosure",
        ),
        _raw_document(
            "20000000-0000-0000-0000-000000000001",
            source_type="news",
            platform="reuters",
        ),
    ]
    linked = [
        LinkedEvidence(
            document=doc,
            link=EventDocument(
                event_id=EVENT_ID,
                document_id=doc.id,
                weight=1.0,
                source_weight=1.0,
                is_duplicate=False,
            ),
        )
        for doc in docs
    ]
    provider_counts = Counter(item.document.platform for item in linked)
    snapshot_at = datetime(2026, 8, 5, 2, 0, tzinfo=UTC)
    updates = [
        build_score_update(item=item, snapshot_at=snapshot_at, provider_counts=provider_counts)
        for item in linked
    ]

    raw = synthesize_raw_score(updates)

    # 事实源 observation=0.92，新闻 observation=0.82；合成结果应落在两者之间
    assert 0.82 <= raw <= 0.92
    # 且校准版本常量与实现一致
    assert SCORING_SYNTHETIC_VERSION == "analysis-pipeline-scoring-v1"
