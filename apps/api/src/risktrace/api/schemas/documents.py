from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: str
    source_level: str
    platform: str
    source_id: str
    source_url: str | None = None
    published_at: datetime
    collected_at: datetime
    received_at: datetime
    replay_at: datetime | None = None
    author_id_hash: str | None = None
    title: str | None = None
    raw_text: str | None = None
    language: str
    engagement: dict | None = None
    is_original: bool | None = None
    collection_method: str
    license_scope: str
    content_hash: str
    raw_payload_ref: str | None = None
    source_metadata: dict[str, object]
    created_at: datetime
