import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.db.models import Entity, Event, EventDocument, EvidenceLink, RawDocument
from risktrace.seed.data import ENTITIES, EVENT, EVENT_DOCUMENTS, EVIDENCE_LINKS, RAW_DOCUMENTS

_SOURCE_LEVEL_BY_TYPE = {
    "fact": "official",
    "news": "professional_media",
    "social": "public_discussion",
    "market": "market_data",
}


class SeedImporter:
    def __init__(self, session: AsyncSession, checkpoint_path: str | None = None) -> None:
        self.session = session
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None

    async def import_all(self) -> dict:
        stats = {
            "event": await self._import_event(),
            "entities": await self._import_entities(),
            "documents": await self._import_documents(),
            "event_documents": await self._link_documents(),
            "evidence_links": await self._import_evidence_links(),
        }
        await self.session.commit()
        self._write_checkpoint(stats)
        return stats

    async def _import_event(self) -> dict[str, int]:
        event_id = EVENT["id"]
        existing = await self.session.get(Event, event_id)
        if existing:
            return {"inserted": 0, "skipped": 1}
        self.session.add(Event(**EVENT))
        return {"inserted": 1, "skipped": 0}

    async def _import_entities(self) -> dict[str, int]:
        inserted = 0
        skipped = 0
        for entity_data in ENTITIES:
            existing = await self.session.get(Entity, entity_data["id"])
            if existing:
                skipped += 1
                continue
            self.session.add(Entity(**entity_data))
            inserted += 1
        return {"inserted": inserted, "skipped": skipped}

    async def _import_documents(self) -> dict[str, int]:
        inserted = 0
        skipped = 0
        for doc_data in RAW_DOCUMENTS:
            values = dict(doc_data)
            values.setdefault("source_level", _SOURCE_LEVEL_BY_TYPE[values["source_type"]])
            values.setdefault("received_at", values["collected_at"])
            values.setdefault("source_metadata", {})
            result = await self.session.execute(
                select(RawDocument).where(
                    RawDocument.tenant_id == values["tenant_id"],
                    RawDocument.platform == values["platform"],
                    RawDocument.source_id == values["source_id"],
                )
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue

            result = await self.session.execute(
                select(RawDocument).where(
                    RawDocument.tenant_id == values["tenant_id"],
                    RawDocument.content_hash == values["content_hash"],
                )
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue

            self.session.add(RawDocument(**values))
            inserted += 1
        return {"inserted": inserted, "skipped": skipped}

    async def _link_documents(self) -> dict[str, int]:
        inserted = 0
        skipped = 0
        for link in EVENT_DOCUMENTS:
            result = await self.session.execute(
                select(EventDocument).where(
                    EventDocument.event_id == link["event_id"],
                    EventDocument.document_id == link["document_id"],
                )
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue
            self.session.add(EventDocument(**link))
            inserted += 1
        return {"inserted": inserted, "skipped": skipped}

    async def _import_evidence_links(self) -> dict[str, int]:
        inserted = 0
        skipped = 0
        for link in EVIDENCE_LINKS:
            result = await self.session.execute(
                select(EvidenceLink).where(
                    EvidenceLink.tenant_id == link["tenant_id"],
                    EvidenceLink.conclusion_type == link["conclusion_type"],
                    EvidenceLink.conclusion_id == link["conclusion_id"],
                    EvidenceLink.document_id == link["document_id"],
                )
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue
            self.session.add(EvidenceLink(**link))
            inserted += 1
        return {"inserted": inserted, "skipped": skipped}

    def _write_checkpoint(self, stats: dict) -> None:
        if not self.checkpoint_path:
            return
        self.checkpoint_path.write_text(
            json.dumps(
                {
                    "last_import_at": datetime.now(tz=UTC).isoformat(),
                    "stats": stats,
                    "status": "complete",
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
