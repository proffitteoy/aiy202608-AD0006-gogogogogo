import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from risktrace.events.admission import AdmissionPolicy, ConfirmationPolicy
from risktrace.events.dedup import exact_content_hash, is_near_duplicate
from risktrace.events.embeddings import SentenceTransformerEmbeddingProvider
from risktrace.events.engine import EventEngine
from risktrace.events.lifecycle import LifecyclePolicy, initial_status_for
from risktrace.events.matching import MatchingPolicy, evidence_weight, update_centroid
from risktrace.events.metrics import (
    EventMetricInputs,
    MetricPolicy,
    source_diversity,
)
from risktrace.events.schemas import (
    AdmissionDecision,
    AdmissionInputs,
    ConfirmationEvidence,
    ConfirmationSourceType,
    EventCandidate,
    EventClaim,
    LifecycleStatus,
    StateChange,
)

NOW = datetime(2026, 8, 4, 6, 0, tzinfo=UTC)


class FakeSentenceTransformer:
    def __init__(self) -> None:
        self.call: dict[str, object] | None = None

    def encode(self, texts: list[str], **kwargs: object) -> list[list[float]]:
        self.call = {"texts": texts, **kwargs}
        return [[0.6, 0.8] for _ in texts]


def claim(**overrides: object) -> EventClaim:
    values: dict[str, object] = {
        "document_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "title": "宁德时代匈牙利工厂暂停生产",
        "subject_entity_keys": ("300750.SZ",),
        "event_type": "production_disruption",
        "state_change": StateChange(
            property="production_status", from_value="normal", to_value="suspended"
        ),
        "published_at": NOW,
        "market_relevance": 0.96,
        "state_change_strength": 0.91,
        "potential_impact": 0.86,
        "source_quality": 0.80,
        "data_completeness": 0.90,
        "embedding": (1.0, 0.0, 0.0),
    }
    values.update(overrides)
    return EventClaim(**values)


def test_event_claim_requires_timezone_and_rejects_unknown_semantic_fields() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        claim(published_at=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError, match="Extra inputs"):
        claim(authoritative_risk_score=0.99)
    with pytest.raises(ValidationError, match="zero vector"):
        claim(embedding=(0.0, 0.0, 0.0))


def test_engine_attaches_a_same_event_but_does_not_call_it_a_duplicate() -> None:
    candidate_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    candidate = EventCandidate(
        id=candidate_id,
        centroid_embedding=(0.99, 0.01, 0.0),
        entity_keys=frozenset({"300750.sz"}),
        event_type="production_disruption",
        last_seen_at=NOW - timedelta(minutes=10),
    )

    result = EventEngine().evaluate(claim(), [candidate])

    assert result.admission.decision is AdmissionDecision.ATTACH
    assert result.admission.matched_event_id == candidate_id
    assert result.admission.matched_similarity == pytest.approx(result.best_match.score)
    assert not is_near_duplicate(
        "财联社：宁德时代匈牙利工厂暂停生产。",
        "宁德时代回应称工厂只是进行设备维护。",
    )


def test_admission_keeps_high_impact_low_quality_information_as_candidate() -> None:
    result = EventEngine().evaluate(claim(source_quality=0.15), [])

    assert result.admission.decision_value >= 0.70
    assert result.admission.decision is AdmissionDecision.WAIT
    assert "source_quality_requires_wait" in result.admission.reasons


def test_admission_hard_gates_and_create_path_are_distinct() -> None:
    policy = AdmissionPolicy()
    dropped = policy.evaluate(AdmissionInputs(0.49, 1.0, 1.0, 1.0, 1.0, 1.0))
    created = EventEngine().evaluate(claim(), [])

    assert dropped.decision is AdmissionDecision.DROP
    assert dropped.reasons == ("market_relevance_below_gate",)
    assert created.admission.decision is AdmissionDecision.ADMIT
    assert initial_status_for(created.admission.decision) is LifecycleStatus.CONFIRMED


def test_matcher_uses_full_similarity_after_the_time_window_filter() -> None:
    matching = MatchingPolicy()
    recent = EventCandidate(
        id=uuid.UUID("00000000-0000-0000-0000-000000000010"),
        centroid_embedding=(1.0, 0.0),
        entity_keys=frozenset({"asset"}),
        event_type="policy",
        last_seen_at=NOW - timedelta(hours=1),
    )
    expired = EventCandidate(
        id=uuid.UUID("00000000-0000-0000-0000-000000000011"),
        centroid_embedding=(1.0, 0.0),
        entity_keys=frozenset({"asset"}),
        event_type="policy",
        last_seen_at=NOW - timedelta(hours=49),
    )

    result = matching.find_best((1.0, 0.0), {"asset"}, "policy", NOW, [expired, recent])

    assert result is not None
    assert result.event_id == recent.id
    assert result.semantic_similarity == pytest.approx(1.0)


def test_weighted_centroid_reduces_duplicate_influence() -> None:
    original_weight = evidence_weight(0.8, is_original=True, is_duplicate=False)
    duplicate_weight = evidence_weight(0.8, is_original=False, is_duplicate=True)
    centroid, total_weight = update_centroid(
        (1.0, 0.0), original_weight, (0.0, 1.0), duplicate_weight
    )

    assert original_weight > duplicate_weight
    assert centroid[0] > centroid[1]
    assert total_weight == pytest.approx(original_weight + duplicate_weight)


def test_exact_hash_normalizes_formatting() -> None:
    assert exact_content_hash(" 同一 条消息 HTTPS://EXAMPLE.COM/a ") == exact_content_hash(
        "同一 条消息"
    )


def test_sentence_transformers_adapter_requests_normalized_embeddings() -> None:
    model = FakeSentenceTransformer()
    provider = SentenceTransformerEmbeddingProvider("local/model", revision="r1")
    provider._model = model

    assert provider.encode(["文本"]) == [[0.6, 0.8]]
    assert provider.model_version == "local/model@r1"
    assert model.call == {
        "texts": ["文本"],
        "convert_to_numpy": True,
        "normalize_embeddings": True,
        "show_progress_bar": False,
    }


def test_source_diversity_uses_normalized_entropy() -> None:
    assert source_diversity({"weibo": 10}) == 0.0
    assert source_diversity({"weibo": 10, "news": 10}) == pytest.approx(1.0)
    assert source_diversity({}) is None


def test_rule3_uses_only_observable_inputs_and_preserves_missingness() -> None:
    result = MetricPolicy().calculate(
        EventMetricInputs(
            message_count_5m=40,
            message_count_1h=120,
            baseline_mean_5m=5.0,
            baseline_std_5m=3.0,
            engagement_percentiles=(0.90, 0.80),
            source_counts={"weibo": 20, "xueqiu": 10, "news": 10},
            authority_scores=(0.20, 0.95),
            covered_platform_count=3,
            expected_platform_count=4,
            previous_heat=0.30,
            source_quality=0.85,
            independent_source_ratio=0.75,
            novelty=0.70,
            market_relevance=0.90,
            potential_impact=0.85,
            market_response=0.60,
            data_completeness=0.90,
        )
    )

    assert 0.0 <= result.heat <= 1.0
    assert result.momentum == pytest.approx(result.heat - 0.30)
    assert result.heat_completeness == pytest.approx(1.0)
    assert 0.0 <= result.raw_score <= 1.0
    assert result.scoring_completeness == pytest.approx(1.0)
    assert result.scoring_version == "deterministic-scoring-v1"

    incomplete = MetricPolicy().calculate(
        EventMetricInputs(
            message_count_5m=5,
            message_count_1h=5,
            baseline_mean_5m=5.0,
            baseline_std_5m=1.0,
            engagement_percentiles=(),
            source_counts={"weibo": 5},
            authority_scores=(),
            covered_platform_count=1,
            expected_platform_count=None,
            previous_heat=None,
            source_quality=0.80,
            independent_source_ratio=0.30,
            novelty=0.60,
            market_relevance=0.75,
            potential_impact=0.80,
            market_response=None,
            data_completeness=0.50,
        )
    )
    assert incomplete.engagement is None
    assert incomplete.coverage is None
    assert incomplete.heat_completeness < 1.0
    assert 0.0 <= incomplete.raw_score <= 1.0
    assert incomplete.scoring_completeness == pytest.approx(0.82)


def test_candidate_confirmation_and_lifecycle_are_explicit() -> None:
    confirmation = ConfirmationPolicy().score(
        [
            ConfirmationEvidence(
                document_id=uuid.UUID("00000000-0000-0000-0000-000000000020"),
                source_type=ConfirmationSourceType.FACT,
                source_reliability=1.0,
                document_confidence=0.95,
                cluster_similarity=0.95,
            )
        ]
    )
    lifecycle = LifecyclePolicy()

    assert confirmation >= 0.70
    assert (
        lifecycle.advance(
            LifecycleStatus.CANDIDATE,
            heat=0.4,
            momentum=0.1,
            low_heat_for=timedelta(0),
            confirmation_score=confirmation,
        )
        is LifecycleStatus.CONFIRMED
    )
    assert (
        lifecycle.advance(
            LifecycleStatus.ACTIVE,
            heat=0.2,
            momentum=-0.2,
            low_heat_for=timedelta(hours=6),
        )
        is LifecycleStatus.COOLING
    )
    assert (
        lifecycle.advance(
            LifecycleStatus.COOLING,
            heat=0.2,
            momentum=-0.1,
            low_heat_for=timedelta(hours=24),
        )
        is LifecycleStatus.CLOSED
    )
    assert (
        lifecycle.advance(
            LifecycleStatus.CLOSED,
            heat=0.7,
            momentum=0.3,
            low_heat_for=timedelta(0),
        )
        is LifecycleStatus.ACTIVE
    )


def test_confirmation_does_not_treat_social_velocity_as_fact_support() -> None:
    policy = ConfirmationPolicy()
    social_evidence = [
        ConfirmationEvidence(
            document_id=uuid.UUID(f"00000000-0000-0000-0000-{index:012d}"),
            source_type=ConfirmationSourceType.SOCIAL,
            source_reliability=0.90,
            document_confidence=0.90,
            cluster_similarity=0.95,
        )
        for index in range(30, 35)
    ]

    result = policy.calculate(social_evidence)

    assert result.social_support > 0.99
    assert result.certainty < policy.threshold
    assert not policy.is_confirmed(social_evidence)
