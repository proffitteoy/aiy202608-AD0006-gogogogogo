from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import SecretStr

from risktrace.core.config import Settings
from risktrace.ingestion.pull_live import (
    IngestionApiClient,
    LivePullRunner,
    build_live_adapter,
)
from risktrace.ingestion.schemas import FetchBatch, SourceRecord


def _record(external_id: str = "item-1") -> SourceRecord:
    return SourceRecord.model_validate(
        {
            "external_id": external_id,
            "source": {
                "provider": "licensed-news",
                "stream": "news-stream",
                "type": "news",
                "level": "professional_media",
                "collection_method": "public_http_api",
                "license_scope": "internal_research",
            },
            "published_at": "2026-08-05T09:30:00+08:00",
            "title": "标题",
            "content": "正文",
            "metadata": {"author": "Reporter"},
        }
    )


@dataclass
class FakeHealth:
    status: str
    checked_at: datetime


class FakeAdapter:
    def __init__(self, batch: FetchBatch) -> None:
        self._batch = batch
        self.descriptor = batch.records[0].source if batch.records else _record().source
        self.last_cursor: str | None = None

    async def fetch(
        self,
        *,
        cursor: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> FetchBatch:
        self.last_cursor = cursor
        return self._batch

    async def healthcheck(self) -> FakeHealth:
        return FakeHealth(status="healthy", checked_at=datetime(2026, 8, 5, 1, 0, tzinfo=UTC))


class FakePoster:
    def __init__(self, outcomes: list[str]) -> None:
        self.outcomes = outcomes
        self.records: list[SourceRecord] = []

    async def post(self, record: SourceRecord) -> dict[str, object]:
        self.records.append(record)
        outcome = self.outcomes.pop(0)
        if outcome == "error":
            raise RuntimeError("ingestion failed")
        return {"outcome": outcome}


class FakeRuntimeRepository:
    def __init__(self, checkpoint: str | None = None) -> None:
        self.checkpoint = checkpoint
        self.saved_checkpoint: str | None = None
        self.success_calls: list[dict[str, object]] = []
        self.failure_calls: list[dict[str, object]] = []

    async def get_checkpoint(self, *, tenant_id, provider: str, stream: str) -> str | None:
        return self.checkpoint

    async def save_checkpoint(self, *, tenant_id, provider: str, stream: str, cursor: str) -> None:
        self.saved_checkpoint = cursor

    async def record_success(
        self,
        *,
        tenant_id,
        provider: str,
        stream: str,
        source_type: str,
        at: datetime,
    ) -> None:
        self.success_calls.append(
            {
                "tenant_id": tenant_id,
                "provider": provider,
                "stream": stream,
                "source_type": source_type,
                "at": at,
            }
        )

    async def record_failure(
        self,
        *,
        tenant_id,
        provider: str,
        stream: str,
        source_type: str,
        error: str,
        at: datetime,
    ) -> None:
        self.failure_calls.append(
            {
                "tenant_id": tenant_id,
                "provider": provider,
                "stream": stream,
                "source_type": source_type,
                "error": error,
                "at": at,
            }
        )


@pytest.mark.asyncio
async def test_live_pull_runner_posts_records_and_advances_checkpoint() -> None:
    batch = FetchBatch(records=(_record("item-1"), _record("item-2")), next_cursor="cursor-2")
    runner = LivePullRunner(
        adapter=FakeAdapter(batch),
        poster=FakePoster(["inserted", "duplicate"]),
        runtime_repository=FakeRuntimeRepository(checkpoint="cursor-1"),
        tenant_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    )

    summary = await runner.run()

    assert summary.fetched_records == 2
    assert summary.inserted_records == 1
    assert summary.duplicate_records == 1
    assert summary.checkpoint_before == "cursor-1"
    assert summary.checkpoint_after == "cursor-2"


@pytest.mark.asyncio
async def test_live_pull_runner_records_failure_without_advancing_checkpoint() -> None:
    batch = FetchBatch(records=(_record("item-1"),), next_cursor="cursor-2")
    repository = FakeRuntimeRepository(checkpoint="cursor-1")
    runner = LivePullRunner(
        adapter=FakeAdapter(batch),
        poster=FakePoster(["error"]),
        runtime_repository=repository,
        tenant_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    )

    with pytest.raises(RuntimeError, match="ingestion failed"):
        await runner.run()

    assert repository.saved_checkpoint is None
    assert repository.success_calls == []
    assert len(repository.failure_calls) == 1


def test_build_live_adapter_requires_snowball_cookie() -> None:
    settings = Settings(
        ingestion_api_token="test-token",
        ingestion_allowed_providers="xueqiu-hot-posts",
        live_pull_snowball_cookie="",
    )

    with pytest.raises(ValueError, match="RISKTRACE_LIVE_PULL_SNOWBALL_COOKIE is empty"):
        build_live_adapter("xueqiu-hot-posts", settings)


def test_ingestion_api_client_uses_unified_ingestion_path() -> None:
    client = IngestionApiClient(
        base_url="http://localhost:8000/api",
        token=SecretStr("test-token"),
    )

    assert client.url == "http://localhost:8000/api/v1/ingestion/items"
