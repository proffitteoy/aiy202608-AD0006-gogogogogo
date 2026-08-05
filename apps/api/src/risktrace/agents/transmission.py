import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.core.config import get_settings
from risktrace.db.models import (
    Entity,
    EventDocument,
    OpinionRecord,
    RawDocument,
    TransmissionEdge,
)
from risktrace.seed.data import ENTITY_IDS


class TransmissionEdgeItem(BaseModel):
    from_entity_id: UUID = Field(description="Source entity ID from the registry")
    to_entity_id: UUID = Field(description="Target entity ID from the registry")
    mechanism: str = Field(description="Description of the transmission mechanism, in Chinese")
    direction: str = Field(description="positive | negative | uncertain")
    horizon: str = Field(description="immediate | short | medium | long")
    evidence_doc_ids: list[UUID] = Field(
        description="Document IDs that support this transmission edge"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence in this edge")


class TransmissionOutput(BaseModel):
    edges: list[TransmissionEdgeItem] = Field(
        max_length=8, description="Candidate transmission edges"
    )


@dataclass
class TransmissionDeps:
    valid_entity_ids: set[UUID]
    valid_doc_ids: set[UUID]


class TransmissionGraphAgent:
    def __init__(self, session: AsyncSession) -> None:
        settings = get_settings()
        model_name = f"{settings.llm_provider}:{settings.llm_model}"
        self.agent = Agent(
            model_name,
            output_type=TransmissionOutput,
            retries={"output": 1},
            deps_type=TransmissionDeps,
            system_prompt=(
                "You are a financial transmission analyst identifying how events propagate "
                "through industries, companies, and markets.\n\n"
                "Rules:\n"
                "- Each edge connects two entities from the provided entity registry.\n"
                "- from_entity_id and to_entity_id MUST be valid UUIDs from the entity "
                "registry.\n"
                "- evidence_doc_ids MUST only contain document IDs from the provided document "
                "list.\n"
                "- Each edge needs at least one evidence document.\n"
                "- direction: positive (利好传导), negative (利空传导), uncertain (不确定).\n"
                "- horizon: immediate (即时), short (短期), medium (中期), long (长期).\n"
                "- mechanism: describe the economic logic of the transmission, in Chinese.\n"
                "- Generate at most 8 edges. Only include edges with clear transmission logic."
            ),
        )
        self._register_validators()
        self.session = session
        self._entity_ids = set(ENTITY_IDS.values())

    def _register_validators(self) -> None:
        agent = self.agent

        @agent.output_validator
        async def validate_entities(
            ctx: object, output: TransmissionOutput
        ) -> TransmissionOutput:
            deps: TransmissionDeps = ctx.deps  # type: ignore[assignment]
            for i, edge in enumerate(output.edges):
                if edge.from_entity_id not in deps.valid_entity_ids:
                    raise ModelRetry(
                        f"Edge {i}: from_entity_id {edge.from_entity_id} not in entity registry"
                    )
                if edge.to_entity_id not in deps.valid_entity_ids:
                    raise ModelRetry(
                        f"Edge {i}: to_entity_id {edge.to_entity_id} not in entity registry"
                    )
                if not edge.evidence_doc_ids:
                    raise ModelRetry(
                        f"Edge {i}: must have at least one evidence document"
                    )
                for doc_id in edge.evidence_doc_ids:
                    if doc_id not in deps.valid_doc_ids:
                        raise ModelRetry(
                            f"Edge {i}: evidence_doc_id {doc_id} not in valid document list"
                        )
            return output

    async def generate_for_event(self, event_id: UUID) -> list[TransmissionEdge]:
        docs_result = await self.session.execute(
            select(RawDocument)
            .join(EventDocument, EventDocument.document_id == RawDocument.id)
            .where(EventDocument.event_id == event_id)
        )
        documents = docs_result.scalars().all()
        if not documents:
            return []

        entities_result = await self.session.execute(select(Entity))
        entities = entities_result.scalars().all()

        opinions_result = await self.session.execute(
            select(OpinionRecord).where(OpinionRecord.event_id == event_id)
        )
        opinions = opinions_result.scalars().all()

        tenant_id = documents[0].tenant_id
        valid_doc_ids = {doc.id for doc in documents}

        entity_lines = "\n".join(
            f"  {e.name} ({e.entity_type}): {e.id}" for e in entities
        )
        doc_lines = "\n".join(
            f"  {doc.id}: [{doc.source_type}] {doc.title or 'N/A'}"
            for doc in documents
        )
        opinion_lines = "\n".join(
            f"  doc={o.document_id} entity={o.target_entity_id} stance={o.stance} "
            f"reason={o.reason[:100]}"
            for o in opinions
        ) if opinions else "  (no opinions extracted yet)"

        prompt = (
            f"Entity Registry:\n{entity_lines}\n\n"
            f"Event Documents:\n{doc_lines}\n\n"
            f"Extracted Opinions:\n{opinion_lines}\n\n"
            f"Identify transmission paths between entities based on the above information."
        )
        input_hash = hashlib.sha256(
            json.dumps(
                {"event": str(event_id), "docs": sorted(str(d) for d in valid_doc_ids)},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:64]

        existing = await self.session.execute(
            select(TransmissionEdge).where(
                TransmissionEdge.event_id == event_id,
                TransmissionEdge.input_hash == input_hash,
            )
        )
        if existing.scalars().all():
            return []

        deps = TransmissionDeps(
            valid_entity_ids={e.id for e in entities},
            valid_doc_ids=valid_doc_ids,
        )

        try:
            run_result = await self.agent.run(prompt, deps=deps)
            output: TransmissionOutput = run_result.output
        except Exception:
            return []

        records: list[TransmissionEdge] = []
        for edge in output.edges:
            from_entity = next(
                (e for e in entities if e.id == edge.from_entity_id), None
            )
            to_entity = next(
                (e for e in entities if e.id == edge.to_entity_id), None
            )
            record = TransmissionEdge(
                tenant_id=tenant_id,
                event_id=event_id,
                from_node_type=from_entity.entity_type if from_entity else "unknown",
                from_node_id=edge.from_entity_id,
                to_node_type=to_entity.entity_type if to_entity else "unknown",
                to_node_id=edge.to_entity_id,
                mechanism=edge.mechanism,
                direction=edge.direction,
                horizon=edge.horizon,
                evidence_ids=edge.evidence_doc_ids,
                knowledge_ids=[],
                model_confidence=edge.confidence,
                status="candidate",
                model_version="0.1.0",
                prompt_version="v1",
                input_hash=input_hash,
            )
            self.session.add(record)
            records.append(record)

        if records:
            await self.session.commit()
        return records
