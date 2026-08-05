from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from risktrace.ingestion.adapters.base import (
    AdapterHealth,
    filter_time_range,
    merge_metadata,
    timed_call,
    utc_now,
)
from risktrace.ingestion.adapters.http import HttpRequest, HttpTransport, decode_json
from risktrace.ingestion.schemas import FetchBatch, SourceDescriptor, SourceRecord

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _coerce_datetime(value: object, fallback: datetime) -> datetime:
    if isinstance(value, int | float):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, tz=UTC)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return fallback
    return fallback


class SnowballClient:
    def __init__(
        self,
        *,
        cookie: str,
        transport: HttpTransport | None = None,
    ) -> None:
        self.cookie = cookie
        self.transport = transport or HttpTransport()

    def hot_posts(
        self,
        *,
        scope: str = "day",
        count: int = 20,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        request = HttpRequest(
            method="GET",
            url="https://xueqiu.com/statuses/hots.json",
            params={
                "a": "1",
                "count": str(count),
                "page": str(page),
                "scope": scope,
                "type": "status",
                "meigu": "0",
            },
            headers={
                "User-Agent": _UA,
                "Accept": "application/json",
                "Origin": "https://xueqiu.com",
                "Referer": "https://xueqiu.com/",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": self.cookie,
            },
        )
        payload = decode_json(self.transport.send(request))
        if not isinstance(payload, list):
            raise ValueError("unexpected snowball payload")
        rows: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            author = item.get("user") if isinstance(item.get("user"), dict) else {}
            description = (
                str(item.get("description") or item.get("text") or "")
                .replace("<br>", "\n")
                .replace("&nbsp;", " ")
            )
            post_id = str(item.get("id") or "")
            if not post_id:
                identity = json.dumps(item, ensure_ascii=False, sort_keys=True)
                post_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
            rows.append(
                {
                    "id": post_id,
                    "title": str(item.get("title") or "").strip() or None,
                    "content": description.strip() or str(item.get("title") or "").strip(),
                    "author": author.get("screen_name"),
                    "author_id": author.get("id"),
                    "followers_count": author.get("followers_count"),
                    "likes": item.get("like_count") or item.get("fav_count"),
                    "comments": item.get("reply_count"),
                    "reposts": item.get("retweet_count"),
                    "views": item.get("view_count"),
                    "published_at": _coerce_datetime(item.get("created_at"), utc_now()),
                    "url": (
                        f"https://xueqiu.com{item['target']}"
                        if isinstance(item.get("target"), str) and item["target"]
                        else None
                    ),
                    "raw_item": item,
                }
            )
        return rows


class SnowballHotPostsAdapter:
    def __init__(
        self,
        *,
        cookie: str,
        scope: str = "day",
        count: int = 20,
        stream: str = "xueqiu-hot-posts",
        collection_method: str = "authenticated_web_api",
        license_scope: str = "internal_research",
        client: SnowballClient | None = None,
    ) -> None:
        self.scope = scope
        self.count = count
        self.client = client or SnowballClient(cookie=cookie)
        self._descriptor = SourceDescriptor(
            provider="xueqiu-hot-posts",
            stream=stream,
            type="social",
            level="public_discussion",
            collection_method=collection_method,
            license_scope=license_scope,
        )

    @property
    def descriptor(self) -> SourceDescriptor:
        return self._descriptor

    async def fetch(
        self,
        *,
        cursor: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> FetchBatch:
        page = max(int(cursor or "1"), 1)
        collected_at = utc_now()
        rows = filter_time_range(
            self.client.hot_posts(scope=self.scope, count=self.count, page=page),
            timestamp_key="published_at",
            start_time=start_time,
            end_time=end_time,
        )
        records = tuple(self._to_record(row, collected_at=collected_at) for row in rows)
        return FetchBatch(records=records, next_cursor=str(page + 1))

    async def healthcheck(self) -> AdapterHealth:
        _, latency_ms = timed_call(lambda: self.client.hot_posts(scope=self.scope, count=1, page=1))
        return AdapterHealth(
            status="healthy",
            checked_at=utc_now(),
            detail="authenticated_xueqiu_hot_posts_ok",
            latency_ms=latency_ms,
        )

    def _to_record(self, row: dict[str, Any], *, collected_at: datetime) -> SourceRecord:
        engagement = {
            "likes": row["likes"],
            "comments": row["comments"],
            "reposts": row["reposts"],
            "views": row["views"],
        }
        engagement = {key: value for key, value in engagement.items() if isinstance(value, int)}
        metadata = merge_metadata(
            {
                "author": row["author"],
                "author_id": row["author_id"],
                "author_followers": row["followers_count"],
            },
            adapter_name="snowball_hot_posts",
            extra={
                "scope": self.scope,
                "raw_item": json.dumps(row["raw_item"], ensure_ascii=False),
            },
        )
        payload: dict[str, object] = {
            "external_id": row["id"],
            "source": self.descriptor.model_dump(),
            "published_at": row["published_at"],
            "collected_at": collected_at,
            "title": row["title"],
            "content": row["content"],
            "url": row["url"],
            "language": "zh-CN",
            "metadata": metadata,
            "raw_payload_ref": f"xueqiu-hot-post:{row['id']}",
        }
        if engagement:
            payload["engagement"] = engagement
        return SourceRecord.model_validate(payload)
