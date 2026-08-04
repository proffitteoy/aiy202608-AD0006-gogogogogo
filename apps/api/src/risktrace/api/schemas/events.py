from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from risktrace.api.schemas.common import PaginatedResponse


class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: str
    first_published_at: datetime
    document_count: int
    source_breakdown: dict[str, int]
    latest_activity: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EventDetail(EventSummary):
    pass


class EventListResponse(PaginatedResponse[EventSummary]):
    pass


class TimelineBucket(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    counts: dict[str, int]


class LinkedDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    source_type: str
    platform: str
    published_at: datetime
    weight: float
    engagement: dict | None = None


class WorkspaceResponse(BaseModel):
    event: EventSummary
    timeline: list[TimelineBucket]
    linked_documents: list[LinkedDocument]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    source_type: str
    platform: str
    published_at: datetime
    source_url: str | None = None
    engagement: dict | None = None
    raw_text_preview: str


class EvidenceListResponse(PaginatedResponse[EvidenceItem]):
    pass
