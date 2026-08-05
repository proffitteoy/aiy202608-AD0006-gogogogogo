import enum
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SourceType(enum.StrEnum):
    FACT = "fact"
    NEWS = "news"
    SOCIAL = "social"
    MARKET = "market"


class SourceLevel(enum.StrEnum):
    OFFICIAL = "official"
    PROFESSIONAL_MEDIA = "professional_media"
    PUBLIC_DISCUSSION = "public_discussion"
    MARKET_DATA = "market_data"


_LEVEL_BY_TYPE = {
    SourceType.FACT: SourceLevel.OFFICIAL,
    SourceType.NEWS: SourceLevel.PROFESSIONAL_MEDIA,
    SourceType.SOCIAL: SourceLevel.PUBLIC_DISCUSSION,
    SourceType.MARKET: SourceLevel.MARKET_DATA,
}


class SourceDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    stream: str = Field(default="default", min_length=1, max_length=128)
    type: SourceType
    level: SourceLevel
    collection_method: ShortText = Field(max_length=128)
    license_scope: ShortText = Field(max_length=128)

    @model_validator(mode="after")
    def require_matching_level(self) -> "SourceDescriptor":
        expected = _LEVEL_BY_TYPE[self.type]
        if self.level is not expected:
            raise ValueError(f"source level for {self.type.value} must be {expected.value}")
        return self


class Engagement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    reposts: int | None = Field(default=None, ge=0)
    views: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_observed_value(self) -> "Engagement":
        if all(value is None for value in (self.likes, self.comments, self.reposts, self.views)):
            raise ValueError("engagement must contain at least one observed value")
        return self


class SourceRecord(BaseModel):
    """Source-only contract shared by live adapters and historical replay."""

    model_config = ConfigDict(extra="forbid")

    external_id: ShortText = Field(max_length=255)
    source: SourceDescriptor
    published_at: datetime
    collected_at: datetime | None = None
    replay_at: datetime | None = None
    title: str | None = Field(default=None, max_length=10_000)
    content: str = Field(min_length=1, max_length=2_000_000)
    url: HttpUrl | None = None
    language: str = Field(default="zh-CN", min_length=2, max_length=16)
    engagement: Engagement | None = None
    is_original: bool | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    raw_payload_ref: str | None = Field(default=None, max_length=2_000)

    @field_validator("published_at", "collected_at", "replay_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(UTC)

    @field_validator("title")
    @classmethod
    def normalize_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("content")
    @classmethod
    def require_nonblank_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content cannot be blank")
        return normalized

    @field_validator("metadata")
    @classmethod
    def reject_authoritative_fields(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        forbidden = {
            "tenant_id",
            "event_id",
            "sentiment",
            "risk",
            "risk_score",
            "raw_score",
            "calibrated_score",
            "topic",
        }
        rejected = sorted(forbidden & {key.casefold() for key in value})
        if rejected:
            raise ValueError(
                "metadata cannot contain downstream authority fields: " + ", ".join(rejected)
            )
        return value


class RejectedSourceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: int = Field(ge=1)
    reason: str
    external_id: str | None = None


class FetchBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: tuple[SourceRecord, ...] = ()
    rejected: tuple[RejectedSourceItem, ...] = ()
    next_cursor: str | None = None


class IngestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["inserted", "duplicate"]
    document_id: UUID
    receipt_id: UUID
    duplicate_of_document_id: UUID | None = None
    received_at: datetime
    processing_status: Literal["pending_enrichment"] = "pending_enrichment"
