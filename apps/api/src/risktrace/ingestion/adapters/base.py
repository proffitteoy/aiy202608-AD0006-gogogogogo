from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from risktrace.ingestion.schemas import FetchBatch, SourceDescriptor


class AdapterHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy", "degraded", "unavailable"]
    checked_at: datetime
    detail: str | None = None
    latency_ms: float | None = Field(default=None, ge=0.0)


class SourceAdapter(Protocol):
    @property
    def descriptor(self) -> SourceDescriptor: ...

    async def fetch(
        self,
        *,
        cursor: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> FetchBatch: ...

    async def healthcheck(self) -> AdapterHealth: ...


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def iso_cursor(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def filter_time_range(
    items: list[dict[str, object]],
    *,
    timestamp_key: str,
    start_time: datetime | None,
    end_time: datetime | None,
) -> list[dict[str, object]]:
    filtered: list[dict[str, object]] = []
    start_utc = start_time.astimezone(UTC) if start_time is not None else None
    end_utc = end_time.astimezone(UTC) if end_time is not None else None
    for item in items:
        published_at = item.get(timestamp_key)
        if not isinstance(published_at, datetime):
            continue
        current = published_at.astimezone(UTC)
        if start_utc is not None and current < start_utc:
            continue
        if end_utc is not None and current > end_utc:
            continue
        filtered.append(item)
    return filtered


def timed_call[T](func: Callable[[], T]) -> tuple[T, float]:
    started = time.perf_counter()
    result = func()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return result, elapsed_ms


def merge_metadata(
    base: Mapping[str, object] | None = None,
    *,
    adapter_name: str,
    extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    metadata = dict(base or {})
    metadata["_risktrace_adapter"] = adapter_name
    if extra:
        metadata.update(extra)
    return metadata
