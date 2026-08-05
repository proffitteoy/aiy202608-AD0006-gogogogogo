"""Analysis pipeline orchestrator.

Wires the existing agents into a single sequential flow so the UI can observe
each stage as it runs. Every stage emits at least ``stage_start`` and
``stage_done``; long stages also emit ``stage_progress`` / ``item`` events so
that the client-side timeline shows meaningful motion instead of a blank wait.

The orchestrator is deliberately transport-agnostic: it takes an ``emit``
callback and lets the caller decide whether to fan the events out over SSE,
WebSocket, or an in-memory buffer for tests.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.agents.entities import EntityExtractionAgent
from risktrace.agents.impact import compute_impact_matrix
from risktrace.agents.opinions import OpinionExtractionAgent
from risktrace.agents.transmission import TransmissionGraphAgent
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import (
    Entity,
    Event,
    EventDocument,
    EventMetric,
    EventScoreCalibration,
    OpinionRecord,
    RawDocument,
    TransmissionEdge,
)
from risktrace.ingestion.pipeline import (
    LinkedEvidence,
    aggregate_data_completeness,
    build_score_update,
)
from risktrace.scoring import (
    CalibrationEngine,
    ScoreCalibrationInput,
    calibration_record,
)
from risktrace.scoring.schemas import ScoreEvidenceUpdate

logger = logging.getLogger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]

# 每个阶段的展示 label + 建议持续时间提示（前端可以据此渲染进度条速率）
STAGE_LABELS: dict[str, str] = {
    "ingest": "读取事件证据",
    "entities": "识别涉事主体",
    "opinions": "归因观点抽取",
    "transmission": "构造传导假设",
    "impact": "计算影响矩阵",
    "scoring": "评分校准与置信区间",
}

SCORING_SYNTHETIC_VERSION = "analysis-pipeline-scoring-v1"


def synthesize_raw_score(updates: list[ScoreEvidenceUpdate]) -> float:
    total_iw = sum(update.information_weight for update in updates)
    if total_iw <= 0:
        return 0.5
    weighted = sum(update.observation * update.information_weight for update in updates)
    return max(0.0, min(weighted / total_iw, 1.0))


def synthetic_metric_calculation_id(
    event_id: uuid.UUID,
    document_ids: list[str],
) -> uuid.UUID:
    fingerprint = hashlib.sha256(
        "|".join((str(event_id), SCORING_SYNTHETIC_VERSION, *sorted(document_ids))).encode(
            "utf-8"
        )
    ).hexdigest()
    return uuid.uuid5(uuid.NAMESPACE_URL, f"risktrace-synth-metric:{fingerprint}")


@dataclass(slots=True)
class StageResult:
    stage: str
    produced: int
    skipped: bool = False
    note: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class AnalysisPipeline:
    """串行编排 5 个阶段并把过程事件发到 ``emit``。"""

    def __init__(
        self,
        session: AsyncSession,
        event_id: uuid.UUID,
        emit: EmitFn,
        *,
        force: bool = False,
    ) -> None:
        self.session = session
        self.event_id = event_id
        self.emit = emit
        self.force = force
        self.tenant_id = get_demo_tenant_id()
        self._started_at: float | None = None

    async def _stage_start(self, stage: str, **extra: Any) -> None:
        payload = {"stage": stage, "label": STAGE_LABELS[stage], **extra}
        await self.emit("stage_start", payload)

    async def _stage_progress(self, stage: str, **extra: Any) -> None:
        await self.emit("stage_progress", {"stage": stage, **extra})

    async def _stage_item(self, stage: str, payload: dict[str, Any]) -> None:
        await self.emit("item", {"stage": stage, "payload": payload})

    async def _stage_done(self, result: StageResult) -> None:
        await self.emit(
            "stage_done",
            {
                "stage": result.stage,
                "produced": result.produced,
                "skipped": result.skipped,
                "note": result.note,
                **result.payload,
            },
        )

    async def _stage_error(self, stage: str, error: str) -> None:
        await self.emit("stage_error", {"stage": stage, "error": error})

    async def run(self) -> dict[str, Any]:
        self._started_at = time.perf_counter()
        event = await self.session.scalar(
            select(Event).where(
                Event.id == self.event_id,
                Event.tenant_id == self.tenant_id,
            )
        )
        if event is None:
            await self.emit(
                "fatal",
                {"error": f"Event {self.event_id} not found"},
            )
            return {"ok": False, "reason": "event_not_found"}

        await self.emit(
            "pipeline_start",
            {
                "event_id": str(event.id),
                "event_title": event.title,
                "stages": list(STAGE_LABELS.keys()),
            },
        )

        summary: dict[str, StageResult] = {}
        stages_to_run: tuple[tuple[str, Any], ...] = (
            ("ingest", lambda: self._run_ingest(event.title)),
            ("entities", self._run_entities),
            ("opinions", self._run_opinions),
            ("transmission", self._run_transmission),
            ("impact", self._run_impact),
            ("scoring", lambda: self._run_scoring(event)),
        )
        try:
            for stage_key, runner in stages_to_run:
                result = await runner()
                summary[stage_key] = result
                await self._stage_done(result)
        except Exception as exc:  # noqa: BLE001 -- surface to client, don't crash stream
            logger.exception("Pipeline failed for event %s", self.event_id)
            await self.emit("fatal", {"error": str(exc)})
            return {"ok": False, "reason": "exception", "detail": str(exc)}

        elapsed_ms = int((time.perf_counter() - (self._started_at or 0)) * 1000)
        await self.emit(
            "done",
            {
                "elapsed_ms": elapsed_ms,
                "summary": {
                    stage: {
                        "produced": r.produced,
                        "skipped": r.skipped,
                        "note": r.note,
                    }
                    for stage, r in summary.items()
                },
            },
        )
        return {"ok": True, "elapsed_ms": elapsed_ms}

    async def _run_ingest(self, event_title: str) -> StageResult:
        stage = "ingest"
        await self._stage_start(stage, title=event_title)

        links = (
            await self.session.execute(
                select(EventDocument).where(EventDocument.event_id == self.event_id)
            )
        ).scalars().all()
        doc_ids = [link.document_id for link in links]
        total = len(doc_ids)

        if not doc_ids:
            return StageResult(stage=stage, produced=0, skipped=True, note="事件未关联文档。")

        docs = (
            await self.session.execute(
                select(RawDocument).where(
                    RawDocument.id.in_(doc_ids),
                    RawDocument.tenant_id == self.tenant_id,
                )
            )
        ).scalars().all()
        docs_by_id = {d.id: d for d in docs}

        for idx, doc_id in enumerate(doc_ids, start=1):
            doc = docs_by_id.get(doc_id)
            if doc is None:
                continue
            await self._stage_item(
                stage,
                {
                    "id": str(doc.id),
                    "title": (doc.title or "（无标题）")[:80],
                    "source": doc.source_type,
                    "platform": doc.platform,
                },
            )
            await self._stage_progress(stage, current=idx, total=total)
            await asyncio.sleep(0.05)

        return StageResult(stage=stage, produced=total)

    async def _run_entities(self) -> StageResult:
        stage = "entities"
        await self._stage_start(stage)

        edges = (
            await self.session.execute(
                select(TransmissionEdge).where(
                    TransmissionEdge.event_id == self.event_id,
                    TransmissionEdge.tenant_id == self.tenant_id,
                )
            )
        ).scalars().all()
        edge_entity_ids = {
            node_id
            for edge in edges
            for node_id in (edge.from_node_id, edge.to_node_id)
        }

        should_extract = self.force or not edge_entity_ids

        if should_extract:
            await self._stage_progress(stage, message="调用 LLM 抽取涉事主体…")

            token_buffer: list[str] = []
            char_count = 0

            async def flush_tokens() -> None:
                nonlocal token_buffer
                if not token_buffer:
                    return
                chunk = "".join(token_buffer)
                token_buffer = []
                await self.emit(
                    "llm_delta",
                    {"stage": stage, "delta": chunk, "total_chars": char_count},
                )

            async def relay(event_name: str, payload: dict[str, Any]) -> None:
                nonlocal char_count
                if event_name == "doc_seen":
                    await self._stage_item(stage, {"kind": "doc", **payload})
                elif event_name == "llm_start":
                    await self._stage_progress(
                        stage,
                        message=f"LLM 开始流式生成（{payload.get('model')}）",
                    )
                elif event_name == "llm_delta":
                    delta = str(payload.get("delta", ""))
                    char_count += len(delta)
                    token_buffer.append(delta)
                    if sum(len(t) for t in token_buffer) >= 48:
                        await flush_tokens()
                elif event_name == "llm_done":
                    await flush_tokens()
                    await self._stage_progress(
                        stage,
                        message=f"LLM 完成 · 输出 {payload.get('bytes')} 字符",
                    )
                elif event_name == "entity_accepted":
                    await self._stage_item(stage, {"kind": "entity", **payload})

            agent = EntityExtractionAgent(self.session, emit=relay)
            try:
                accepted = await agent.extract_for_event(self.event_id)
            except (ValueError, RuntimeError) as exc:
                await flush_tokens()
                await self._stage_error(stage, str(exc))
                return StageResult(
                    stage=stage, produced=0, skipped=True, note=str(exc)
                )

            await flush_tokens()
            return StageResult(
                stage=stage,
                produced=len(accepted),
                note=(
                    f"抽取 {len(accepted)} 个涉事主体（其中 "
                    f"{sum(1 for a in accepted if a.reused)} 个复用已有登记）"
                ),
            )

        # 复用已有传导边覆盖的实体；避免每次运行都消耗 LLM 额度
        entities = (
            await self.session.execute(
                select(Entity).where(
                    Entity.id.in_(edge_entity_ids),
                    Entity.tenant_id == self.tenant_id,
                )
            )
        ).scalars().all()

        for entity in entities[:12]:
            await self._stage_item(
                stage,
                {
                    "kind": "entity",
                    "id": str(entity.id),
                    "name": entity.name,
                    "type": entity.entity_type,
                    "reused": True,
                },
            )
            await asyncio.sleep(0.05)

        return StageResult(
            stage=stage,
            produced=len(entities),
            note="使用既有传导图节点（未重新调用 LLM）",
        )

    async def _run_opinions(self) -> StageResult:
        stage = "opinions"
        await self._stage_start(stage)

        if self.force:
            deleted = await self.session.execute(
                delete(OpinionRecord).where(
                    OpinionRecord.event_id == self.event_id,
                    OpinionRecord.tenant_id == self.tenant_id,
                )
            )
            await self.session.commit()
            await self._stage_progress(
                stage,
                message=f"强制重跑：已清除既有观点 {deleted.rowcount or 0} 条",
            )

        existing = (
            await self.session.execute(
                select(OpinionRecord)
                .where(
                    OpinionRecord.event_id == self.event_id,
                    OpinionRecord.tenant_id == self.tenant_id,
                )
                .order_by(OpinionRecord.model_confidence.desc())
            )
        ).scalars().all()

        if existing:
            await self._stage_progress(
                stage,
                message=f"复用既有观点 {len(existing)} 条",
            )
            for op in existing[:10]:
                await self._stage_item(
                    stage,
                    {
                        "kind": "opinion",
                        "id": str(op.id),
                        "stance": op.stance,
                        "emotion": op.emotion,
                        "summary": (op.reason or "")[:80],
                        "reused": True,
                    },
                )
                await asyncio.sleep(0.05)
            return StageResult(
                stage=stage,
                produced=len(existing),
                note="使用既有归因观点（未重新调用 LLM）",
            )

        await self._stage_progress(stage, message="调用 LLM 抽取归因观点…")

        token_buffer: list[str] = []
        char_count = 0

        async def flush_tokens() -> None:
            nonlocal token_buffer
            if not token_buffer:
                return
            chunk = "".join(token_buffer)
            token_buffer = []
            await self.emit(
                "llm_delta",
                {"stage": stage, "delta": chunk, "total_chars": char_count},
            )

        async def relay(event_name: str, payload: dict[str, Any]) -> None:
            nonlocal char_count
            if event_name == "doc_seen":
                await self._stage_item(stage, {"kind": "doc", **payload})
            elif event_name == "llm_start":
                await self._stage_progress(
                    stage,
                    message=f"LLM 开始流式生成（{payload.get('model')}）",
                )
            elif event_name == "llm_delta":
                delta = str(payload.get("delta", ""))
                char_count += len(delta)
                token_buffer.append(delta)
                if sum(len(t) for t in token_buffer) >= 48:
                    await flush_tokens()
            elif event_name == "llm_done":
                await flush_tokens()
                await self._stage_progress(
                    stage,
                    message=f"LLM 完成 · 输出 {payload.get('bytes')} 字符",
                )
            elif event_name == "opinion_accepted":
                await self._stage_item(stage, {"kind": "opinion", **payload})

        agent = OpinionExtractionAgent(self.session, emit=relay)
        try:
            rows = await agent.extract_for_event(self.event_id)
        except (ValueError, RuntimeError) as exc:
            await flush_tokens()
            await self._stage_error(stage, str(exc))
            return StageResult(stage=stage, produced=0, skipped=True, note=str(exc))

        await flush_tokens()
        return StageResult(stage=stage, produced=len(rows))

    async def _run_transmission(self) -> StageResult:
        stage = "transmission"
        await self._stage_start(stage)

        if self.force:
            deleted = await self.session.execute(
                delete(TransmissionEdge).where(
                    TransmissionEdge.event_id == self.event_id,
                    TransmissionEdge.tenant_id == self.tenant_id,
                )
            )
            await self.session.commit()
            await self._stage_progress(
                stage,
                message=f"强制重跑：已清除既有边 {deleted.rowcount or 0} 条",
            )

        existing_count = (
            await self.session.execute(
                select(func.count())
                .select_from(TransmissionEdge)
                .where(
                    TransmissionEdge.event_id == self.event_id,
                    TransmissionEdge.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one()

        # 已有边就复用；避免每次运行都消耗 LLM 额度且改动置信度分布
        if existing_count > 0:
            await self._stage_progress(
                stage,
                message=f"复用既有传导候选 {existing_count} 条",
            )
            edges = (
                await self.session.execute(
                    select(TransmissionEdge)
                    .where(
                        TransmissionEdge.event_id == self.event_id,
                        TransmissionEdge.tenant_id == self.tenant_id,
                    )
                    .order_by(TransmissionEdge.model_confidence.desc())
                    .limit(6)
                )
            ).scalars().all()
            for edge in edges:
                await self._stage_item(
                    stage,
                    {
                        "id": str(edge.id),
                        "mechanism": edge.mechanism,
                        "direction": edge.direction,
                        "confidence": float(edge.model_confidence),
                        "status": edge.status,
                    },
                )
                await asyncio.sleep(0.08)
            return StageResult(
                stage=stage,
                produced=existing_count,
                note="使用既有候选（未重新调用 LLM）",
            )

        await self._stage_progress(stage, message="调用 LLM 生成候选…")

        # Buffer LLM tokens so we flush at most ~10 fps to the browser.
        token_buffer: list[str] = []
        char_count = 0

        async def flush_tokens() -> None:
            nonlocal token_buffer
            if not token_buffer:
                return
            chunk = "".join(token_buffer)
            token_buffer = []
            await self.emit(
                "llm_delta",
                {"stage": stage, "delta": chunk, "total_chars": char_count},
            )

        async def relay(event_name: str, payload: dict[str, Any]) -> None:
            nonlocal char_count
            if event_name == "doc_seen":
                await self._stage_item(stage, {"kind": "doc", **payload})
            elif event_name == "llm_start":
                await self._stage_progress(
                    stage,
                    message=f"LLM 开始流式生成（{payload.get('model')}）",
                )
            elif event_name == "llm_delta":
                delta = str(payload.get("delta", ""))
                char_count += len(delta)
                token_buffer.append(delta)
                if sum(len(t) for t in token_buffer) >= 48:
                    await flush_tokens()
            elif event_name == "llm_done":
                await flush_tokens()
                await self._stage_progress(
                    stage,
                    message=f"LLM 完成 · 输出 {payload.get('bytes')} 字符",
                )
            elif event_name == "edge_accepted":
                await self._stage_item(stage, {"kind": "edge", **payload})

        agent = TransmissionGraphAgent(self.session, emit=relay)
        try:
            new_edges = await agent.generate_for_event(self.event_id)
        except ValueError as exc:
            await flush_tokens()
            await self._stage_error(stage, str(exc))
            return StageResult(stage=stage, produced=0, skipped=True, note=str(exc))
        except RuntimeError as exc:
            await flush_tokens()
            await self._stage_error(stage, str(exc))
            return StageResult(stage=stage, produced=0, skipped=True, note=str(exc))

        await flush_tokens()
        return StageResult(stage=stage, produced=len(new_edges))

    async def _run_impact(self) -> StageResult:
        stage = "impact"
        await self._stage_start(stage)

        async def relay(event_name: str, payload: dict[str, Any]) -> None:
            if event_name == "matrix_scan_start":
                await self._stage_progress(
                    stage,
                    total=payload.get("total"),
                    current=0,
                    message=f"扫描 {payload.get('total')} 个候选主体…",
                )
            elif event_name == "entity_scored":
                await self._stage_progress(
                    stage,
                    current=payload.get("index"),
                    total=payload.get("total"),
                )
                await self._stage_item(stage, {"kind": "scored", **payload})
            elif event_name == "entity_skipped":
                await self._stage_progress(
                    stage,
                    current=payload.get("index"),
                    total=payload.get("total"),
                )

        rows = await compute_impact_matrix(
            self.event_id,
            self.session,
            emit=relay,
            row_delay=0.05,
        )
        return StageResult(stage=stage, produced=len(rows))

    async def _run_scoring(self, event: Event) -> StageResult:
        stage = "scoring"
        await self._stage_start(stage)

        linked = await self._load_linked_evidence()
        if not linked:
            return StageResult(
                stage=stage,
                produced=0,
                skipped=True,
                note="事件未关联文档，跳过评分校准。",
            )
        await self._stage_progress(
            stage,
            message=f"载入证据 {len(linked)} 条",
        )

        if self.force:
            deleted = await self.session.execute(
                delete(EventScoreCalibration).where(
                    EventScoreCalibration.event_id == self.event_id,
                    EventScoreCalibration.tenant_id == self.tenant_id,
                )
            )
            if deleted.rowcount:
                await self._stage_progress(
                    stage,
                    message=f"强制重跑：已清除既有校准 {deleted.rowcount} 条",
                )

        metric, metric_source = await self._resolve_scoring_metric(event, linked)
        await self._stage_progress(
            stage,
            message=(
                f"使用 {'既有 metric' if metric_source == 'metric' else '合成 metric'} · "
                f"raw={metric.raw_score:.3f}"
            ),
        )

        provider_counts = Counter(item.document.platform for item in linked)
        updates = [
            build_score_update(
                item=item,
                snapshot_at=metric.metric_at,
                provider_counts=provider_counts,
            )
            for item in linked
        ]
        market_completeness = (
            1.0 if any(item.document.source_type == "market" for item in linked) else None
        )
        calibration_input = ScoreCalibrationInput(
            tenant_id=event.tenant_id,
            event_id=event.id,
            score_calculation_id=metric.calculation_id,
            raw_score=metric.raw_score or 0.0,
            scoring_version=metric.scoring_version,
            data_completeness=min(
                aggregate_data_completeness(linked),
                metric.scoring_completeness,
            ),
            source_health=1.0,
            market_data_completeness=market_completeness,
        )

        calculation = CalibrationEngine().calculate(calibration_input, updates)

        existing = await self.session.scalar(
            select(EventScoreCalibration).where(
                EventScoreCalibration.calculation_id == calculation.calculation_id,
            )
        )
        reused = existing is not None
        if not reused:
            self.session.add(calibration_record(calculation, snapshot_at=metric.metric_at))

        event.raw_score = calculation.raw_score
        event.calibrated_score = calculation.calibrated_score
        event.score_confidence = calculation.confidence
        event.score_lower_bound = calculation.score_interval.lower
        event.score_upper_bound = calculation.score_interval.upper
        event.scoring_version = calculation.scoring_version
        event.calibration_version = calculation.calibration_version

        await self.session.commit()

        await self._stage_item(
            stage,
            {
                "kind": "summary",
                "raw_score": calculation.raw_score,
                "calibrated_score": calculation.calibrated_score,
                "confidence": calculation.confidence,
                "lower": calculation.score_interval.lower,
                "upper": calculation.score_interval.upper,
                "degradation_reasons": list(calculation.degradation_reasons),
                "snapshot_hash": calculation.evidence_snapshot_hash,
                "scoring_version": calculation.scoring_version,
                "metric_source": metric_source,
            },
        )
        return StageResult(
            stage=stage,
            produced=1,
            note="复用既有校准记录" if reused else None,
            payload={"metric_source": metric_source},
        )

    async def _load_linked_evidence(self) -> list[LinkedEvidence]:
        rows = (
            await self.session.execute(
                select(EventDocument, RawDocument)
                .join(RawDocument, RawDocument.id == EventDocument.document_id)
                .where(
                    EventDocument.event_id == self.event_id,
                    RawDocument.tenant_id == self.tenant_id,
                )
            )
        ).all()
        return [LinkedEvidence(document=doc, link=link) for link, doc in rows]

    async def _resolve_scoring_metric(
        self,
        event: Event,
        linked: list[LinkedEvidence],
    ) -> tuple[EventMetric, str]:
        metric = await self.session.scalar(
            select(EventMetric)
            .where(
                EventMetric.event_id == self.event_id,
                EventMetric.tenant_id == self.tenant_id,
                EventMetric.raw_score.is_not(None),
            )
            .order_by(EventMetric.metric_at.desc())
            .limit(1)
        )
        if metric is not None:
            return metric, "metric"
        return await self._synthesize_scoring_metric(event, linked), "synthetic"

    async def _synthesize_scoring_metric(
        self,
        event: Event,
        linked: list[LinkedEvidence],
    ) -> EventMetric:
        provider_counts = Counter(item.document.platform for item in linked)
        metric_at = event.last_seen_at
        updates = [
            build_score_update(
                item=item,
                snapshot_at=metric_at,
                provider_counts=provider_counts,
            )
            for item in linked
        ]
        synthetic_raw = synthesize_raw_score(updates)
        doc_ids_sorted = sorted(str(item.document.id) for item in linked)
        calculation_id = synthetic_metric_calculation_id(event.id, doc_ids_sorted)

        existing = await self.session.scalar(
            select(EventMetric).where(EventMetric.calculation_id == calculation_id)
        )
        if existing is not None:
            return existing

        completeness = aggregate_data_completeness(linked)
        doc_count = len(linked)
        metric = EventMetric(
            calculation_id=calculation_id,
            tenant_id=event.tenant_id,
            event_id=event.id,
            metric_at=metric_at,
            bucket_minutes=5,
            msg_count_5m=doc_count,
            msg_count_1h=doc_count,
            volume=min(doc_count / 10.0, 1.0),
            growth_z=0.0,
            growth=0.5,
            engagement=None,
            diversity=None,
            authority=None,
            coverage=None,
            heat=min(doc_count / 10.0, 1.0),
            heat_completeness=completeness,
            momentum=None,
            raw_score=synthetic_raw,
            scoring_completeness=completeness,
            scoring_version=SCORING_SYNTHETIC_VERSION,
            input_document_ids=doc_ids_sorted,
            parameters={
                "synthesized_by": "agents.pipeline._run_scoring",
                "evidence_count": doc_count,
            },
        )
        self.session.add(metric)
        await self.session.flush()
        return metric
