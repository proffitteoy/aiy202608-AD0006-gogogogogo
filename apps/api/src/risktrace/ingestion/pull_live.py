from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from pydantic import SecretStr

from risktrace.core.config import Settings
from risktrace.ingestion.adapters import (
    CailianpressTelegraphAdapter,
    CailianpressTelegraphClient,
    SnowballClient,
    SnowballHotPostsAdapter,
    SourceAdapter,
    TencentQuoteAdapter,
    TencentQuoteClient,
)
from risktrace.ingestion.adapters.http import HttpRequest, HttpTransport, decode_json
from risktrace.ingestion.schemas import SourceRecord


class IngestionPoster(Protocol):
    async def post(self, record: SourceRecord) -> dict[str, object]: ...


class SourceRuntimeRepository(Protocol):
    async def get_checkpoint(
        self,
        *,
        tenant_id,
        provider: str,
        stream: str,
    ) -> str | None: ...

    async def save_checkpoint(
        self,
        *,
        tenant_id,
        provider: str,
        stream: str,
        cursor: str,
    ) -> None: ...

    async def record_success(
        self,
        *,
        tenant_id,
        provider: str,
        stream: str,
        source_type: str,
        at: datetime,
    ) -> None: ...

    async def record_failure(
        self,
        *,
        tenant_id,
        provider: str,
        stream: str,
        source_type: str,
        error: str,
        at: datetime,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class PullSummary:
    adapter_name: str
    fetched_records: int
    rejected_records: int
    inserted_records: int
    duplicate_records: int
    checkpoint_before: str | None
    checkpoint_after: str | None
    health_status: str | None


class IngestionApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: SecretStr,
        transport: HttpTransport | None = None,
    ) -> None:
        normalized_base = base_url.rstrip("/")
        if normalized_base.endswith("/api"):
            self.url = f"{normalized_base}/v1/ingestion/items"
        else:
            self.url = f"{normalized_base}/api/v1/ingestion/items"
        self.token = token.get_secret_value()
        self.transport = transport or HttpTransport()

    async def post(self, record: SourceRecord) -> dict[str, object]:
        request = HttpRequest(
            method="POST",
            url=self.url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            body=record.model_dump_json().encode("utf-8"),
        )
        response = self.transport.send(request)
        payload = decode_json(response)
        if response.status_code >= 400:
            detail = payload if isinstance(payload, dict) else {"detail": str(payload)}
            raise RuntimeError(json.dumps(detail, ensure_ascii=False))
        if not isinstance(payload, dict):
            raise RuntimeError("unexpected ingestion response payload")
        return payload


class LivePullRunner:
    def __init__(
        self,
        *,
        adapter: SourceAdapter,
        poster: IngestionPoster,
        runtime_repository: SourceRuntimeRepository,
        tenant_id,
    ) -> None:
        self.adapter = adapter
        self.poster = poster
        self.runtime_repository = runtime_repository
        self.tenant_id = tenant_id

    async def run(
        self,
        *,
        cursor: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip_healthcheck: bool = False,
    ) -> PullSummary:
        descriptor = self.adapter.descriptor
        checkpoint_before = cursor
        if checkpoint_before is None:
            checkpoint_before = await self.runtime_repository.get_checkpoint(
                tenant_id=self.tenant_id,
                provider=descriptor.provider,
                stream=descriptor.stream,
            )

        health_status: str | None = None
        checked_at = None
        try:
            if not skip_healthcheck:
                health = await self.adapter.healthcheck()
                health_status = health.status
                checked_at = health.checked_at

            batch = await self.adapter.fetch(
                cursor=checkpoint_before,
                start_time=start_time,
                end_time=end_time,
            )
            inserted = 0
            duplicate = 0
            for record in batch.records:
                response = await self.poster.post(record)
                outcome = response.get("outcome")
                if outcome == "inserted":
                    inserted += 1
                elif outcome == "duplicate":
                    duplicate += 1
                else:
                    raise RuntimeError(f"unexpected ingestion outcome: {outcome!r}")

            if batch.next_cursor is not None:
                await self.runtime_repository.save_checkpoint(
                    tenant_id=self.tenant_id,
                    provider=descriptor.provider,
                    stream=descriptor.stream,
                    cursor=batch.next_cursor,
                )
            success_at = checked_at or datetime.now(tz=UTC)
            await self.runtime_repository.record_success(
                tenant_id=self.tenant_id,
                provider=descriptor.provider,
                stream=descriptor.stream,
                source_type=descriptor.type.value,
                at=success_at,
            )
        except Exception as exc:
            failure_at = checked_at or datetime.now(tz=UTC)
            await self.runtime_repository.record_failure(
                tenant_id=self.tenant_id,
                provider=descriptor.provider,
                stream=descriptor.stream,
                source_type=descriptor.type.value,
                error=str(exc),
                at=failure_at,
            )
            raise

        return PullSummary(
            adapter_name=descriptor.provider,
            fetched_records=len(batch.records),
            rejected_records=len(batch.rejected),
            inserted_records=inserted,
            duplicate_records=duplicate,
            checkpoint_before=checkpoint_before,
            checkpoint_after=batch.next_cursor,
            health_status=health_status,
        )


def available_live_adapter_names() -> tuple[str, ...]:
    return ("tencent-quote", "cailianpress-telegraph", "xueqiu-hot-posts")


def build_live_adapter(name: str, settings: Settings) -> SourceAdapter:
    transport = HttpTransport(timeout_seconds=settings.live_pull_request_timeout_seconds)
    if name == "tencent-quote":
        symbols = [
            item.strip()
            for item in settings.live_pull_tencent_symbols.split(",")
            if item.strip()
        ]
        if not symbols:
            raise ValueError("RISKTRACE_LIVE_PULL_TENCENT_SYMBOLS is empty")
        return TencentQuoteAdapter(
            symbols=symbols,
            stream=settings.live_pull_tencent_stream,
            license_scope=settings.live_pull_license_scope,
            client=TencentQuoteClient(transport=transport),
        )
    if name == "cailianpress-telegraph":
        return CailianpressTelegraphAdapter(
            page_size=settings.live_pull_cls_page_size,
            stream=settings.live_pull_cls_stream,
            license_scope=settings.live_pull_license_scope,
            client=CailianpressTelegraphClient(transport=transport),
        )
    if name == "xueqiu-hot-posts":
        cookie = settings.live_pull_snowball_cookie.get_secret_value()
        if not cookie:
            raise ValueError("RISKTRACE_LIVE_PULL_SNOWBALL_COOKIE is empty")
        return SnowballHotPostsAdapter(
            cookie=cookie,
            scope=settings.live_pull_snowball_scope,
            count=settings.live_pull_snowball_count,
            stream=settings.live_pull_snowball_stream,
            license_scope=settings.live_pull_license_scope,
            client=SnowballClient(cookie=cookie, transport=transport),
        )
    raise ValueError(f"unsupported live adapter: {name}")
