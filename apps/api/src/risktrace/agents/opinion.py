import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.core.config import get_settings
from risktrace.db.models import EventDocument, OpinionRecord, RawDocument
from risktrace.seed.data import ENTITY_IDS


class OpinionOutput(BaseModel):
    has_opinion: bool = Field(description="Whether the text contains an opinion about the event")
    target_entity_id: UUID | None = Field(
        default=None, description="Target entity ID from the registry, or null"
    )
    stance: str = Field(description="bullish | bearish | neutral | wait")
    emotion: str = Field(description="Emotion label, e.g. optimism, fear, anger, calm, uncertainty")
    reason: str = Field(description="Concise reason for the opinion, in Chinese")
    claim_type: str = Field(description="fact | opinion | speculation")
    evidence_span: str = Field(
        description="Verbatim text span from the document that supports this opinion"
    )
    model_confidence: float = Field(
        ge=0.0, le=1.0, description="Model confidence in this extraction"
    )


@dataclass
class OpinionDeps:
    raw_text: str
    valid_entity_ids: set[UUID]


class OpinionExtractor:
    def __init__(self, session: AsyncSession) -> None:
        settings = get_settings()
        model_name = f"{settings.llm_provider}:{settings.llm_small_model}"
        self.agent = Agent(
            model_name,
            output_type=OpinionOutput,
            retries={"output": 1},
            deps_type=OpinionDeps,
            system_prompt=(
                "You are a financial sentiment analyst extracting structured opinions from Chinese "
                "financial news and social media posts about market events.\n\n"
                "Rules:\n"
                "- evidence_span MUST be a verbatim substring of the input text.\n"
                "- target_entity_id MUST be one of the entity IDs provided in the context, "
                "or null.\n"
                "- stance: bullish (看多), bearish (看空), neutral (中性), wait (观望).\n"
                "- claim_type: fact (事实陈述), opinion (主观观点), speculation (推测).\n"
                "- emotion: pick the dominant emotion from optimism/fear/anger/calm/uncertainty.\n"
                "- If the text has no clear opinion about the event, set has_opinion=false."
            ),
        )
        self._register_validators()
        self.session = session
        self._entity_ids = set(ENTITY_IDS.values())

    def _register_validators(self) -> None:
        agent = self.agent

        @agent.output_validator
        async def validate_evidence_span(
            ctx: object, output: OpinionOutput
        ) -> OpinionOutput:
            if not output.has_opinion:
                return output
            deps: OpinionDeps = ctx.deps  # type: ignore[assignment]
            if output.evidence_span not in deps.raw_text:
                raise ModelRetry(
                    f"evidence_span must be a verbatim substring of the input text. "
                    f"'{output.evidence_span[:80]}' was not found."
                )
            return output

        @agent.output_validator
        async def validate_entity_id(
            ctx: object, output: OpinionOutput
        ) -> OpinionOutput:
            if not output.has_opinion:
                return output
            deps: OpinionDeps = ctx.deps  # type: ignore[assignment]
            if (
                output.target_entity_id is not None
                and output.target_entity_id not in deps.valid_entity_ids
            ):
                raise ModelRetry(
                    f"target_entity_id {output.target_entity_id} is not in the entity registry. "
                    f"Use null or a valid ID from the context."
                )
            return output

    async def extract_for_event(self, event_id: UUID) -> list[OpinionRecord]:
        result = await self.session.execute(
            select(RawDocument)
            .join(EventDocument, EventDocument.document_id == RawDocument.id)
            .where(EventDocument.event_id == event_id)
        )
        documents = result.scalars().all()

        if not documents:
            return []

        entity_list = "\n".join(
            f"  {name}: {eid}" for name, eid in ENTITY_IDS.items()
        )
        records: list[OpinionRecord] = []

        for doc in documents:
            prompt = (
                f"Entity Registry:\n{entity_list}\n\n"
                f"Document title: {doc.title or 'N/A'}\n"
                f"Source type: {doc.source_type}\n"
                f"Text:\n{doc.raw_text or ''}"
            )
            input_hash = hashlib.sha256(
                json.dumps({"text": doc.raw_text, "event": str(event_id)}, sort_keys=True).encode()
            ).hexdigest()[:64]

            existing = await self.session.execute(
                select(OpinionRecord).where(
                    OpinionRecord.document_id == doc.id,
                    OpinionRecord.input_hash == input_hash,
                )
            )
            if existing.scalar_one_or_none():
                continue

            deps = OpinionDeps(
                raw_text=doc.raw_text or "",
                valid_entity_ids=self._entity_ids,
            )

            try:
                run_result = await self.agent.run(prompt, deps=deps)
                output: OpinionOutput = run_result.output
            except Exception:
                continue

            if not output.has_opinion:
                continue

            record = OpinionRecord(
                tenant_id=doc.tenant_id,
                event_id=event_id,
                document_id=doc.id,
                target_entity_id=output.target_entity_id,
                stance=output.stance,
                emotion=output.emotion,
                reason=output.reason,
                claim_type=output.claim_type,
                evidence_span=output.evidence_span,
                model_confidence=output.model_confidence,
                model_version="0.1.0",
                prompt_version="v1",
                input_hash=input_hash,
            )
            self.session.add(record)
            records.append(record)

        if records:
            await self.session.commit()
        return records
