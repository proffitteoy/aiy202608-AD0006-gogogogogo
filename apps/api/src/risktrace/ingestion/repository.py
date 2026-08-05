import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.db.models import (
    IngestionReceipt,
    RawDocument,
    SourceCheckpoint,
    SourceHealth,
    SourceHealthStatus,
)


class ImmutableSourceConflictError(ValueError):
    def __init__(self, document_id: uuid.UUID) -> None:
        self.document_id = document_id
        super().__init__("source identity already exists with different immutable content")


@dataclass(frozen=True, slots=True)
class StoredIngestion:
    outcome: str
    document_id: uuid.UUID
    receipt_id: uuid.UUID
    duplicate_of_document_id: uuid.UUID | None
    received_at: datetime


_IMMUTABLE_FIELDS = (
    "tenant_id",
    "source_type",
    "source_level",
    "platform",
    "source_id",
    "source_url",
    "published_at",
    "author_id_hash",
    "title",
    "raw_text",
    "language",
    "engagement",
    "is_original",
    "collection_method",
    "license_scope",
    "content_hash",
    "raw_payload_ref",
    "source_metadata",
)


def immutable_values_match(existing: RawDocument, values: dict[str, object]) -> bool:
    return all(getattr(existing, field) == values[field] for field in _IMMUTABLE_FIELDS)


class SqlAlchemyIngestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def store(
        self,
        *,
        values: dict[str, object],
        provider: str,
        stream: str,
        received_at: datetime,
        replay_at: datetime | None,
    ) -> StoredIngestion:
        document_id = uuid.uuid4()
        statement = (
            insert(RawDocument)
            .values(id=document_id, **values)
            .on_conflict_do_nothing(
                index_elements=["tenant_id", "platform", "source_id"]
            )
            .returning(RawDocument.id)
        )
        inserted_id = await self.session.scalar(statement)
        outcome = "inserted"

        if inserted_id is None:
            existing = await self.session.scalar(
                select(RawDocument).where(
                    RawDocument.tenant_id == values["tenant_id"],
                    RawDocument.platform == values["platform"],
                    RawDocument.source_id == values["source_id"],
                )
            )
            if existing is None:
                raise RuntimeError("source identity conflict did not return an existing document")
            if not immutable_values_match(existing, values):
                raise ImmutableSourceConflictError(existing.id)
            document_id = existing.id
            outcome = "duplicate"

        content_duplicate_id = await self.session.scalar(
            select(RawDocument.id)
            .where(
                RawDocument.tenant_id == values["tenant_id"],
                RawDocument.content_hash == values["content_hash"],
                RawDocument.id != document_id,
            )
            .order_by(RawDocument.created_at, RawDocument.id)
            .limit(1)
        )
        receipt = IngestionReceipt(
            tenant_id=values["tenant_id"],
            document_id=document_id,
            provider=provider,
            stream=stream,
            received_at=received_at,
            replay_at=replay_at,
            outcome=outcome,
            processing_status="pending_enrichment",
        )
        self.session.add(receipt)
        await self.session.flush()
        return StoredIngestion(
            outcome=outcome,
            document_id=document_id,
            receipt_id=receipt.id,
            duplicate_of_document_id=content_duplicate_id,
            received_at=received_at,
        )


class SqlAlchemySourceRuntimeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_checkpoint(
        self,
        *,
        tenant_id: uuid.UUID,
        provider: str,
        stream: str,
    ) -> str | None:
        return await self.session.scalar(
            select(SourceCheckpoint.cursor).where(
                SourceCheckpoint.tenant_id == tenant_id,
                SourceCheckpoint.provider == provider,
                SourceCheckpoint.stream == stream,
            )
        )

    async def save_checkpoint(
        self,
        *,
        tenant_id: uuid.UUID,
        provider: str,
        stream: str,
        cursor: str,
    ) -> None:
        statement = insert(SourceCheckpoint).values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider=provider,
            stream=stream,
            cursor=cursor,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_source_checkpoints_stream",
            set_={"cursor": cursor, "updated_at": datetime.now(tz=UTC)},
        )
        await self.session.execute(statement)

    async def record_success(
        self,
        *,
        tenant_id: uuid.UUID,
        provider: str,
        stream: str,
        source_type: str,
        at: datetime,
    ) -> None:
        statement = insert(SourceHealth).values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider=provider,
            stream=stream,
            source_type=source_type,
            status=SourceHealthStatus.HEALTHY.value,
            consecutive_failures=0,
            last_success_at=at,
            last_error=None,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_source_health_stream",
            set_={
                "source_type": source_type,
                "status": SourceHealthStatus.HEALTHY.value,
                "consecutive_failures": 0,
                "last_success_at": at,
                "last_error": None,
                "updated_at": at,
            },
        )
        await self.session.execute(statement)

    async def record_failure(
        self,
        *,
        tenant_id: uuid.UUID,
        provider: str,
        stream: str,
        source_type: str,
        error: str,
        at: datetime,
    ) -> None:
        current = await self.session.scalar(
            select(SourceHealth).where(
                SourceHealth.tenant_id == tenant_id,
                SourceHealth.provider == provider,
                SourceHealth.stream == stream,
            )
        )
        failures = (current.consecutive_failures if current else 0) + 1
        status = (
            SourceHealthStatus.UNAVAILABLE.value
            if failures >= 5
            else SourceHealthStatus.DEGRADED.value
        )
        if current is None:
            self.session.add(
                SourceHealth(
                    tenant_id=tenant_id,
                    provider=provider,
                    stream=stream,
                    source_type=source_type,
                    status=status,
                    consecutive_failures=failures,
                    last_failure_at=at,
                    last_error=error[:2_000],
                )
            )
            return
        current.source_type = source_type
        current.status = status
        current.consecutive_failures = failures
        current.last_failure_at = at
        current.last_error = error[:2_000]
