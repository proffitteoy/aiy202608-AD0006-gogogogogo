from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class SourceType(StrEnum):
    FACT = "fact"
    NEWS = "news"
    SOCIAL = "social"
    MARKET = "market"


class ReplayState(StrEnum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"


def parse_aware_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"datetime must include a timezone: {value!r}")
    return parsed.astimezone(UTC)


def format_datetime(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include a timezone")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    provider: str
    stream: str
    type: SourceType
    level: str
    collection_method: str
    license_scope: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("source provider must not be empty")
        if not self.stream.strip():
            raise ValueError("source stream must not be empty")
        if not self.level.strip():
            raise ValueError("source level must not be empty")
        if not self.collection_method.strip():
            raise ValueError("collection_method must not be empty")
        if not self.license_scope.strip():
            raise ValueError("license_scope must not be empty")

    def to_dict(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "stream": self.stream,
            "type": self.type.value,
            "level": self.level,
            "collection_method": self.collection_method,
            "license_scope": self.license_scope,
        }


@dataclass(frozen=True, slots=True)
class SourceRecord:
    external_id: str
    source: SourceDescriptor
    published_at: datetime
    collected_at: datetime
    title: str
    content: str
    url: str | None
    language: str
    content_hash: str
    raw_payload_ref: str
    author: str | None = None
    engagement: dict[str, int] | None = None
    is_original: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            "external_id": self.external_id,
            "title": self.title,
            "content": self.content,
            "language": self.language,
            "raw_payload_ref": self.raw_payload_ref,
        }
        for name, value in required.items():
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        format_datetime(self.published_at)
        format_datetime(self.collected_at)
        if len(self.content_hash) != 64 or any(
            character not in "0123456789abcdef" for character in self.content_hash
        ):
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        if self.engagement is not None and any(value < 0 for value in self.engagement.values()):
            raise ValueError("engagement values must not be negative")

    def to_dict(self) -> dict[str, Any]:
        metadata = {
            **self.metadata,
            "content_hash": self.content_hash,
        }
        if self.author is not None:
            metadata["author"] = self.author
        return {
            "external_id": self.external_id,
            "source": self.source.to_dict(),
            "published_at": format_datetime(self.published_at),
            "collected_at": format_datetime(self.collected_at),
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "language": self.language,
            "engagement": self.engagement,
            "is_original": self.is_original,
            "metadata": metadata,
            "raw_payload_ref": self.raw_payload_ref,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SourceRecord:
        source = value["source"]
        return cls(
            external_id=value["external_id"],
            source=SourceDescriptor(
                provider=source["provider"],
                stream=source.get("stream", "default"),
                type=SourceType(source["type"]),
                level=source["level"],
                collection_method=source["collection_method"],
                license_scope=source["license_scope"],
            ),
            published_at=parse_aware_datetime(value["published_at"]),
            collected_at=parse_aware_datetime(value["collected_at"]),
            title=value["title"],
            content=value["content"],
            url=value.get("url"),
            language=value["language"],
            content_hash=value["metadata"]["content_hash"],
            raw_payload_ref=value["raw_payload_ref"],
            author=value.get("metadata", {}).get("author"),
            engagement=(dict(value["engagement"]) if value.get("engagement") is not None else None),
            is_original=value.get("is_original"),
            metadata={
                key: item
                for key, item in value.get("metadata", {}).items()
                if key not in {"author", "content_hash"}
            },
        )

    def to_ingestion_payload(
        self,
        *,
        replay_at: datetime,
        scenario_id: str,
        sequence: int,
    ) -> dict[str, Any]:
        payload = self.to_dict()
        payload["replay_at"] = format_datetime(replay_at)
        payload["metadata"] = {
            **payload["metadata"],
            "scenario_id": scenario_id,
            "sequence": sequence,
        }
        return payload


@dataclass(frozen=True, slots=True)
class RejectedRecord:
    source_document: str
    paragraph_start: int
    heading: str
    reason: str
    detail: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "source_document": self.source_document,
            "paragraph_start": self.paragraph_start,
            "heading": self.heading,
            "reason": self.reason,
            "detail": self.detail,
        }
