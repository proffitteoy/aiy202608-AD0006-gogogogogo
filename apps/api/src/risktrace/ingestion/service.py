import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from risktrace.events.dedup import exact_content_hash
from risktrace.ingestion.repository import StoredIngestion
from risktrace.ingestion.schemas import SourceRecord


class IngestionStore(Protocol):
    async def store(
        self,
        *,
        values: dict[str, object],
        provider: str,
        stream: str,
        received_at: datetime,
        replay_at: datetime | None,
    ) -> StoredIngestion: ...


def _author_hash(metadata: dict[str, object]) -> str | None:
    author = metadata.get("author_id") or metadata.get("author")
    if not author:
        return None
    serialized = json.dumps(author, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class IngestionService:
    def __init__(
        self,
        store: IngestionStore,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.now = now or (lambda: datetime.now(tz=UTC))

    async def ingest(self, record: SourceRecord, *, tenant_id: uuid.UUID) -> StoredIngestion:
        received_at = self.now().astimezone(UTC)
        collected_at = record.collected_at or received_at
        source_metadata = dict(record.metadata)
        source_metadata["_risktrace_ingestion"] = {
            "engagement_available": record.engagement is not None,
            "stream": record.source.stream,
        }
        content_for_hash = f"{record.title or ''}\n\n{record.content}"
        values: dict[str, object] = {
            "tenant_id": tenant_id,
            "source_type": record.source.type.value,
            "source_level": record.source.level.value,
            "platform": record.source.provider,
            "source_id": record.external_id,
            "source_url": str(record.url) if record.url is not None else None,
            "published_at": record.published_at,
            "collected_at": collected_at,
            "received_at": received_at,
            "replay_at": record.replay_at,
            "author_id_hash": _author_hash(record.metadata),
            "title": record.title,
            "raw_text": record.content,
            "language": record.language,
            "engagement": (
                record.engagement.model_dump(exclude_none=True)
                if record.engagement is not None
                else {}
            ),
            "is_original": record.is_original,
            "collection_method": record.source.collection_method,
            "license_scope": record.source.license_scope,
            "content_hash": exact_content_hash(content_for_hash),
            "raw_payload_ref": record.raw_payload_ref,
            "source_metadata": source_metadata,
        }
        return await self.store.store(
            values=values,
            provider=record.source.provider,
            stream=record.source.stream,
            received_at=received_at,
            replay_at=record.replay_at,
        )
