import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.db.models import Event


class EventCandidateRepository:
    """Tenant-scoped pgvector shortlist for the deterministic event matcher."""

    async def shortlist(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        embedding: Sequence[float],
        published_at: datetime,
        window: timedelta = timedelta(hours=48),
        limit: int = 20,
    ) -> list[Event]:
        if not embedding:
            raise ValueError("embedding is required")
        if published_at.tzinfo is None or published_at.utcoffset() is None:
            raise ValueError("published_at must include a timezone")
        if limit <= 0:
            raise ValueError("limit must be positive")
        distance = Event.centroid_embedding.cosine_distance(list(embedding))
        statement = (
            select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.last_seen_at >= published_at - window,
                Event.last_seen_at <= published_at + window,
                Event.centroid_embedding.is_not(None),
                func.vector_dims(Event.centroid_embedding) == len(embedding),
            )
            .order_by(distance, Event.id)
            .limit(limit)
        )
        return list((await session.scalars(statement)).all())
