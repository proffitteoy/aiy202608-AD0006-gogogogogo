from __future__ import annotations

import hashlib
import logging
import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.db.models import (
    Event,
    EventAdmissionRecord,
    EventDocument,
    EventMetric,
    EvidenceLink,
    EventScoreCalibration,
    RawDocument,
)
from risktrace.events.admission import ConfirmationPolicy
from risktrace.events.dedup import first_duplicate_index, normalize_text
from risktrace.events.engine import EventEngine
from risktrace.events.lifecycle import LifecyclePolicy, initial_status_for
from risktrace.events.matching import evidence_weight, initial_centroid, update_centroid
from risktrace.events.metrics import EventMetricInputs, MetricPolicy
from risktrace.events.schemas import (
    AdmissionDecision,
    ConfirmationEvidence,
    ConfirmationSourceType,
    EventCandidate,
    EventClaim,
    LifecycleStatus,
    StateChange,
)
from risktrace.scoring import (
    CalibrationEngine,
    EvidenceWeightComponents,
    ScoreCalibrationInput,
    ScoreEvidenceUpdate,
    calibration_record,
)

logger = logging.getLogger(__name__)

_CANONICAL_KEY_PATTERN = re.compile(r"[^a-z0-9:_-]+")
_EMBEDDING_DIMENSIONS = 32
_PIPELINE_VERSION = "deterministic-ingestion-pipeline-v1"

_SOURCE_QUALITY_BY_LEVEL = {
    "official": 0.95,
    "professional_media": 0.82,
    "public_discussion": 0.64,
    "market_data": 0.78,
}
_MARKET_RELEVANCE_BY_TYPE = {
    "fact": 0.92,
    "news": 0.82,
    "social": 0.72,
    "market": 0.76,
}
_STATE_CHANGE_BY_TYPE = {
    "fact": 0.92,
    "news": 0.80,
    "social": 0.70,
    "market": 0.68,
}
_IMPACT_BY_TYPE = {
    "fact": 0.88,
    "news": 0.81,
    "social": 0.69,
    "market": 0.74,
}
_OBSERVATION_BY_TYPE = {
    "fact": 0.92,
    "news": 0.82,
    "social": 0.68,
    "market": 0.72,
}
_SCORE_RELEVANCE_BY_TYPE = {
    "fact": 0.96,
    "news": 0.86,
    "social": 0.70,
    "market": 0.62,
}
_SOURCE_TYPE_ORDER = {
    "fact": 0,
    "news": 1,
    "market": 2,
    "social": 3,
}
_CONFIRMATION_TYPE_BY_SOURCE = {
    "fact": ConfirmationSourceType.FACT,
    "news": ConfirmationSourceType.NEWS,
    "social": ConfirmationSourceType.SOCIAL,
}


@dataclass(frozen=True, slots=True)
class LinkedEvidence:
    document: RawDocument
    link: EventDocument


def canonical_key(value: str) -> str:
    normalized = _CANONICAL_KEY_PATTERN.sub("_", value.strip().casefold()).strip("_")
    return normalized[:128] or "unclassified"


def hashed_embedding(text: str, dimensions: int = _EMBEDDING_DIMENSIONS) -> tuple[float, ...]:
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    normalized = normalize_text(text)
    if not normalized:
        normalized = "empty"
    features = [normalized[index : index + 3] for index in range(max(len(normalized) - 2, 1))]
    vector = [0.0] * dimensions
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:2], "big") % dimensions
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        vector[0] = 1.0
        norm = 1.0
    return tuple(value / norm for value in vector)


def document_group_key(document: RawDocument) -> str:
    metadata = document.source_metadata.get("_risktrace_ingestion", {})
    if isinstance(metadata, dict):
        stream = metadata.get("stream")
        if isinstance(stream, str) and stream.strip():
            return canonical_key(stream)
    return canonical_key(f"{document.platform}:{document.source_type}")


def document_completeness(document: RawDocument) -> float:
    score = 0.45
    if document.title:
        score += 0.15
    if document.source_url:
        score += 0.15
    if document.raw_payload_ref:
        score += 0.05
    raw_text = (document.raw_text or "").strip()
    if len(raw_text) >= 120:
        score += 0.10
    elif len(raw_text) >= 40:
        score += 0.05
    if document.engagement:
        score += 0.05
    precision = document.source_metadata.get("published_at_precision")
    if precision == "date":
        score -= 0.05
    return max(0.30, min(score, 1.0))


def source_quality(document: RawDocument) -> float:
    return _SOURCE_QUALITY_BY_LEVEL.get(document.source_level, 0.60)


def build_event_claim(document: RawDocument) -> EventClaim:
    group_key = document_group_key(document)
    title = document.title or first_line(document.raw_text or group_key)
    content = "\n\n".join(part for part in (title, document.raw_text, group_key) if part)
    return EventClaim(
        document_id=document.id,
        title=title,
        subject_entity_keys=(group_key,),
        event_type=group_key,
        state_change=StateChange(
            property="document_state",
            from_value=None,
            to_value=document.source_type,
        ),
        published_at=document.published_at,
        market_relevance=_MARKET_RELEVANCE_BY_TYPE.get(document.source_type, 0.70),
        state_change_strength=_STATE_CHANGE_BY_TYPE.get(document.source_type, 0.70),
        potential_impact=_IMPACT_BY_TYPE.get(document.source_type, 0.70),
        source_quality=source_quality(document),
        data_completeness=document_completeness(document),
        embedding=hashed_embedding(content),
    )


def first_line(value: str, length: int = 120) -> str:
    collapsed = " ".join(value.split())
    if not collapsed:
        return "Untitled event"
    return collapsed[:length]


class DeterministicIngestionPipeline:
    def __init__(
        self,
        session: AsyncSession,
        *,
        event_engine: EventEngine | None = None,
        metric_policy: MetricPolicy | None = None,
        lifecycle_policy: LifecyclePolicy | None = None,
        confirmation_policy: ConfirmationPolicy | None = None,
        calibration_engine: CalibrationEngine | None = None,
    ) -> None:
        self.session = session
        self.event_engine = event_engine or EventEngine()
        self.metric_policy = metric_policy or MetricPolicy()
        self.lifecycle_policy = lifecycle_policy or LifecyclePolicy()
        self.confirmation_policy = confirmation_policy or ConfirmationPolicy()
        self.calibration_engine = calibration_engine or CalibrationEngine()

    async def process_document(self, document_id: uuid.UUID) -> uuid.UUID | None:
        existing_record = await self.session.scalar(
            select(EventAdmissionRecord).where(EventAdmissionRecord.document_id == document_id)
        )
        if existing_record is not None:
            return existing_record.event_id

        document = await self.session.get(RawDocument, document_id)
        if document is None:
            raise ValueError(f"document {document_id} not found")

        claim = build_event_claim(document)
        candidates = await self._load_candidates(document.tenant_id)
        evaluation = self.event_engine.evaluate(claim, candidates)

        event: Event | None = None
        existing_documents: list[LinkedEvidence] = []
        duplicate_of_document_id: uuid.UUID | None = None

        if evaluation.admission.decision is AdmissionDecision.ATTACH:
            event = await self.session.get(Event, evaluation.admission.matched_event_id)
            if event is None:
                raise ValueError("matched event is missing")
            existing_documents = await self._load_event_documents(event.id)
            duplicate_of_document_id = find_duplicate_document_id(document, existing_documents)
            self._update_event_centroid(
                event,
                claim.embedding,
                source_quality=source_quality(document),
                is_original=document.is_original,
                is_duplicate=duplicate_of_document_id is not None,
            )
        elif evaluation.admission.decision in {
            AdmissionDecision.WAIT,
            AdmissionDecision.ADMIT,
        }:
            event = self._build_new_event(document, claim, evaluation)
            self.session.add(event)
            await self.session.flush()

        self.session.add(
            EventAdmissionRecord(
                tenant_id=document.tenant_id or uuid.UUID(int=0),
                document_id=document.id,
                event_id=event.id if event is not None else None,
                decision=evaluation.admission.decision.value,
                market_relevance=claim.market_relevance,
                state_change_strength=claim.state_change_strength,
                potential_impact=claim.potential_impact,
                novelty=evaluation.novelty,
                source_quality=claim.source_quality,
                data_completeness=claim.data_completeness,
                decision_value=evaluation.admission.decision_value,
                matched_similarity=evaluation.admission.matched_similarity,
                rule_version=evaluation.admission.rule_version,
                reasons=list(evaluation.admission.reasons),
            )
        )

        if event is None:
            return None

        if not existing_documents:
            existing_documents = await self._load_event_documents(event.id)
        duplicate_of_document_id = duplicate_of_document_id or find_duplicate_document_id(
            document, existing_documents
        )
        source_weight = evidence_weight(
            claim.source_quality,
            is_original=document.is_original,
            is_duplicate=duplicate_of_document_id is not None,
        )
        self.session.add(
            EventDocument(
                event_id=event.id,
                document_id=document.id,
                weight=source_weight,
                similarity=evaluation.admission.matched_similarity,
                source_weight=claim.source_quality,
                novelty=evaluation.novelty,
                is_duplicate=duplicate_of_document_id is not None,
                duplicate_of_document_id=duplicate_of_document_id,
            )
        )
        await self._ensure_evidence_link(event.id, document.id, document.tenant_id)
        await self.session.flush()

        linked_documents = await self._load_event_documents(event.id)
        confirmation = self._confirmation_score(linked_documents)
        metric = await self._build_metric(
            event=event,
            linked_documents=linked_documents,
            current_document=document,
            novelty=evaluation.novelty,
            market_relevance=claim.market_relevance,
            potential_impact=claim.potential_impact,
        )
        self.session.add(metric)
        calibration = self._build_calibration(
            event=event,
            linked_documents=linked_documents,
            metric=metric,
        )
        self.session.add(calibration)

        event.title = choose_event_title(linked_documents)
        event.summary = (
            f"Deterministically aggregated from {len(linked_documents)} source documents."
        )
        event.last_seen_at = max(item.document.published_at for item in linked_documents)
        event.admission_decision_value = evaluation.admission.decision_value
        event.evidence_count = len(linked_documents)
        event.heat_score = metric.heat
        event.momentum = metric.momentum
        event.raw_score = metric.raw_score
        event.score_confidence = calibration.confidence
        event.calibrated_score = calibration.calibrated_score
        event.score_lower_bound = calibration.lower_bound
        event.score_upper_bound = calibration.upper_bound
        event.scoring_version = metric.scoring_version
        event.calibration_version = calibration.calibration_version
        event.status = self._advance_status(
            current=LifecycleStatus(event.status),
            heat=metric.heat,
            momentum=metric.momentum,
            low_heat_for=await self._low_heat_duration(event.id, metric.metric_at),
            confirmation_score=confirmation,
        ).value
        return event.id

    async def _load_candidates(self, tenant_id: uuid.UUID | None) -> list[EventCandidate]:
        if tenant_id is None:
            return []
        result = await self.session.execute(
            select(Event).where(Event.tenant_id == tenant_id).order_by(Event.last_seen_at.desc())
        )
        candidates: list[EventCandidate] = []
        for event in result.scalars():
            centroid = tuple(float(value) for value in (event.centroid_embedding or []))
            if not centroid:
                centroid = hashed_embedding(event.title or event.event_type or str(event.id))
            event_type = event.event_type or "unclassified"
            candidates.append(
                EventCandidate(
                    id=event.id,
                    centroid_embedding=centroid,
                    entity_keys=frozenset({event_type}),
                    event_type=event_type,
                    last_seen_at=event.last_seen_at,
                )
            )
        return candidates

    async def _load_event_documents(self, event_id: uuid.UUID) -> list[LinkedEvidence]:
        result = await self.session.execute(
            select(RawDocument, EventDocument)
            .join(EventDocument, EventDocument.document_id == RawDocument.id)
            .where(EventDocument.event_id == event_id)
            .order_by(RawDocument.published_at.asc(), RawDocument.id.asc())
        )
        return [
            LinkedEvidence(document=document, link=link)
            for document, link in result.all()
        ]

    async def _ensure_evidence_link(
        self,
        event_id: uuid.UUID,
        document_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
    ) -> None:
        if tenant_id is None:
            return
        existing = await self.session.scalar(
            select(EvidenceLink.id).where(
                EvidenceLink.tenant_id == tenant_id,
                EvidenceLink.conclusion_type == "event",
                EvidenceLink.conclusion_id == event_id,
                EvidenceLink.document_id == document_id,
            )
        )
        if existing is not None:
            return
        self.session.add(
            EvidenceLink(
                tenant_id=tenant_id,
                conclusion_type="event",
                conclusion_id=event_id,
                document_id=document_id,
            )
        )

    def _build_new_event(
        self,
        document: RawDocument,
        claim: EventClaim,
        evaluation: object,
    ) -> Event:
        assert hasattr(evaluation, "admission")
        admission = evaluation.admission
        source_weight = evidence_weight(
            claim.source_quality,
            is_original=document.is_original,
            is_duplicate=False,
        )
        centroid, centroid_weight = initial_centroid(claim.embedding, source_weight)
        initial_status = initial_status_for(admission.decision) or LifecycleStatus.CANDIDATE
        return Event(
            tenant_id=document.tenant_id or uuid.UUID(int=0),
            title=claim.title,
            summary=None,
            event_type=claim.event_type,
            status=initial_status.value,
            first_published_at=document.published_at,
            last_seen_at=document.published_at,
            centroid_embedding=list(centroid),
            centroid_weight=centroid_weight,
            embedding_model="hashed-ngram-v1",
            admission_decision_value=admission.decision_value,
            evidence_count=0,
        )

    def _update_event_centroid(
        self,
        event: Event,
        embedding: Iterable[float],
        *,
        source_quality: float,
        is_original: bool | None,
        is_duplicate: bool,
    ) -> None:
        weight = evidence_weight(
            source_quality,
            is_original=is_original,
            is_duplicate=is_duplicate,
        )
        current_centroid = tuple(float(value) for value in (event.centroid_embedding or []))
        if not current_centroid:
            centroid, total_weight = initial_centroid(tuple(embedding), weight)
        else:
            centroid, total_weight = update_centroid(
                current_centroid,
                event.centroid_weight,
                tuple(float(value) for value in embedding),
                weight,
            )
        event.centroid_embedding = list(centroid)
        event.centroid_weight = total_weight

    def _confirmation_score(self, linked_documents: list[LinkedEvidence]) -> float:
        evidence: list[ConfirmationEvidence] = []
        for item in linked_documents:
            source_type = _CONFIRMATION_TYPE_BY_SOURCE.get(item.document.source_type)
            if source_type is None:
                continue
            evidence.append(
                ConfirmationEvidence(
                    document_id=item.document.id,
                    source_type=source_type,
                    source_reliability=source_quality(item.document),
                    document_confidence=document_completeness(item.document),
                    cluster_similarity=item.link.similarity or 1.0,
                )
            )
        if not evidence:
            return 0.0
        return self.confirmation_policy.score(evidence)

    async def _build_metric(
        self,
        *,
        event: Event,
        linked_documents: list[LinkedEvidence],
        current_document: RawDocument,
        novelty: float,
        market_relevance: float,
        potential_impact: float,
    ) -> EventMetric:
        metric_at = metric_timestamp(linked_documents, current_document.id)
        previous_metric = await self.session.scalar(
            select(EventMetric)
            .where(EventMetric.event_id == event.id)
            .order_by(EventMetric.metric_at.desc())
            .limit(1)
        )
        providers = Counter(item.document.platform for item in linked_documents)
        source_types = Counter(item.document.source_type for item in linked_documents)
        engagement_values = tuple(
            engagement_score(item.document) for item in linked_documents if item.document.engagement
        )
        authority_scores = tuple(source_quality(item.document) for item in linked_documents)
        message_count_5m = count_documents_since(linked_documents, metric_at, timedelta(minutes=5))
        message_count_1h = count_documents_since(linked_documents, metric_at, timedelta(hours=1))
        baseline_mean = max(0.5, previous_metric.msg_count_5m if previous_metric else message_count_5m / 2)
        baseline_std = max(0.5, baseline_mean / 2)
        covered_platform_count = len(source_types)
        event_data_completeness = aggregate_data_completeness(linked_documents)
        metric_result = self.metric_policy.calculate(
            EventMetricInputs(
                message_count_5m=message_count_5m,
                message_count_1h=message_count_1h,
                baseline_mean_5m=baseline_mean,
                baseline_std_5m=baseline_std,
                engagement_percentiles=engagement_values,
                source_counts=providers,
                authority_scores=authority_scores,
                covered_platform_count=covered_platform_count,
                expected_platform_count=4,
                previous_heat=previous_metric.heat if previous_metric is not None else None,
                source_quality=average_value(authority_scores, default=source_quality(current_document)),
                independent_source_ratio=min(len(providers) / max(len(linked_documents), 1), 1.0),
                novelty=max(0.05, novelty),
                market_relevance=market_relevance,
                potential_impact=potential_impact,
                market_response=0.65 if source_types.get("market") else None,
                data_completeness=event_data_completeness,
            )
        )
        input_document_ids = [str(item.document.id) for item in linked_documents]
        calculation_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            ":".join(
                (
                    _PIPELINE_VERSION,
                    str(event.tenant_id),
                    str(event.id),
                    metric_at.isoformat(),
                    metric_result.scoring_version,
                    *input_document_ids,
                )
            ),
        )
        return EventMetric(
            calculation_id=calculation_id,
            tenant_id=event.tenant_id,
            event_id=event.id,
            metric_at=metric_at,
            bucket_minutes=5,
            msg_count_5m=message_count_5m,
            msg_count_1h=message_count_1h,
            volume=metric_result.volume,
            growth_z=metric_result.growth_z,
            growth=metric_result.growth,
            engagement=metric_result.engagement,
            diversity=metric_result.diversity,
            authority=metric_result.authority,
            coverage=metric_result.coverage,
            heat=metric_result.heat,
            heat_completeness=metric_result.heat_completeness,
            momentum=metric_result.momentum,
            raw_score=metric_result.raw_score,
            scoring_completeness=metric_result.scoring_completeness,
            scoring_version=metric_result.scoring_version,
            input_document_ids=input_document_ids,
            parameters={
                "pipeline_version": _PIPELINE_VERSION,
                "baseline_mean_5m": baseline_mean,
                "baseline_std_5m": baseline_std,
                "provider_count": len(providers),
            },
        )

    def _build_calibration(
        self,
        *,
        event: Event,
        linked_documents: list[LinkedEvidence],
        metric: EventMetric,
    ) -> EventScoreCalibration:
        provider_counts = Counter(item.document.platform for item in linked_documents)
        market_data_completeness = 1.0 if any(
            item.document.source_type == "market" for item in linked_documents
        ) else None
        calibration_input = ScoreCalibrationInput(
            tenant_id=event.tenant_id,
            event_id=event.id,
            score_calculation_id=metric.calculation_id,
            raw_score=metric.raw_score or 0.0,
            scoring_version=metric.scoring_version,
            data_completeness=min(
                aggregate_data_completeness(linked_documents),
                metric.scoring_completeness,
            ),
            source_health=1.0,
            market_data_completeness=market_data_completeness,
        )
        updates = [
            build_score_update(
                item=item,
                snapshot_at=metric.metric_at,
                provider_counts=provider_counts,
            )
            for item in linked_documents
        ]
        calculation = self.calibration_engine.calculate(calibration_input, updates)
        return calibration_record(calculation, snapshot_at=metric.metric_at)

    async def _low_heat_duration(
        self,
        event_id: uuid.UUID,
        metric_at: datetime,
    ) -> timedelta:
        latest_high_heat = await self.session.scalar(
            select(EventMetric.metric_at)
            .where(
                EventMetric.event_id == event_id,
                EventMetric.heat >= self.lifecycle_policy.cooling_heat_threshold,
            )
            .order_by(EventMetric.metric_at.desc())
            .limit(1)
        )
        if latest_high_heat is None:
            earliest_metric = await self.session.scalar(
                select(EventMetric.metric_at)
                .where(EventMetric.event_id == event_id)
                .order_by(EventMetric.metric_at.asc())
                .limit(1)
            )
            if earliest_metric is None:
                return timedelta(0)
            return metric_at - earliest_metric
        if metric_at <= latest_high_heat:
            return timedelta(0)
        return metric_at - latest_high_heat

    def _advance_status(
        self,
        *,
        current: LifecycleStatus,
        heat: float,
        momentum: float | None,
        low_heat_for: timedelta,
        confirmation_score: float,
    ) -> LifecycleStatus:
        status = current
        for _ in range(3):
            next_status = self.lifecycle_policy.advance(
                status,
                heat=heat,
                momentum=momentum,
                low_heat_for=low_heat_for,
                confirmation_score=confirmation_score,
            )
            if next_status is status:
                break
            status = next_status
        return status


def find_duplicate_document_id(
    current_document: RawDocument,
    linked_documents: list[LinkedEvidence],
) -> uuid.UUID | None:
    texts = [document_text(item.document) for item in linked_documents]
    duplicate_index = first_duplicate_index(texts, document_text(current_document))
    if duplicate_index is None:
        return None
    return linked_documents[duplicate_index].document.id


def document_text(document: RawDocument) -> str:
    return "\n\n".join(part for part in (document.title, document.raw_text) if part)


def metric_timestamp(linked_documents: list[LinkedEvidence], current_document_id: uuid.UUID) -> datetime:
    current_document = next(
        item.document for item in linked_documents if item.document.id == current_document_id
    )
    same_instant_ids = sorted(
        str(item.document.id)
        for item in linked_documents
        if item.document.published_at == current_document.published_at
    )
    offset = same_instant_ids.index(str(current_document_id))
    return current_document.published_at + timedelta(microseconds=offset)


def choose_event_title(linked_documents: list[LinkedEvidence]) -> str:
    def sort_key(item: LinkedEvidence) -> tuple[int, int, datetime, str]:
        return (
            _SOURCE_TYPE_ORDER.get(item.document.source_type, 99),
            0 if item.document.title else 1,
            item.document.published_at,
            str(item.document.id),
        )

    selected = min(linked_documents, key=sort_key)
    return selected.document.title or first_line(selected.document.raw_text or "Untitled event")


def count_documents_since(
    linked_documents: list[LinkedEvidence],
    metric_at: datetime,
    window: timedelta,
) -> int:
    return sum(
        1
        for item in linked_documents
        if timedelta(0) <= metric_at - item.document.published_at <= window
    )


def engagement_score(document: RawDocument) -> float:
    total = sum(value for value in document.engagement.values() if isinstance(value, int))
    if total <= 0:
        return 0.0
    return min(math.log1p(total) / 12.0, 1.0)


def aggregate_data_completeness(linked_documents: list[LinkedEvidence]) -> float:
    values = [document_completeness(item.document) for item in linked_documents]
    if any(item.document.source_type == "fact" for item in linked_documents):
        values.append(1.0)
    if any(item.document.source_type == "market" for item in linked_documents):
        values.append(1.0)
    return average_value(values, default=0.50)


def average_value(values: Iterable[float], *, default: float) -> float:
    items = list(values)
    if not items:
        return default
    return max(0.0, min(sum(items) / len(items), 1.0))


def build_score_update(
    *,
    item: LinkedEvidence,
    snapshot_at: datetime,
    provider_counts: Counter[str],
) -> ScoreEvidenceUpdate:
    provider_count = max(provider_counts[item.document.platform], 1)
    freshness_hours = max((snapshot_at - item.document.published_at).total_seconds() / 3600, 0.0)
    freshness = max(0.25, 1.0 - min(freshness_hours, 96.0) / 120.0)
    independence = 0.0 if item.link.is_duplicate else min(1.0, 1.0 / provider_count + 0.25)
    return ScoreEvidenceUpdate(
        document_id=item.document.id,
        observation=_OBSERVATION_BY_TYPE.get(item.document.source_type, 0.70),
        weight=EvidenceWeightComponents(
            source_reliability=source_quality(item.document),
            independence=independence,
            score_relevance=_SCORE_RELEVANCE_BY_TYPE.get(item.document.source_type, 0.70),
            freshness=freshness,
            data_quality=document_completeness(item.document),
        ),
    )
