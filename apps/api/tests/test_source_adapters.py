from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from risktrace.ingestion.adapters.a_share import (
    CailianpressTelegraphAdapter,
    CailianpressTelegraphClient,
    TencentQuoteAdapter,
    TencentQuoteClient,
)
from risktrace.ingestion.adapters.http import HttpRequest, HttpResponse
from risktrace.ingestion.adapters.snowball import SnowballClient, SnowballHotPostsAdapter


class FakeTransport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self._responses = responses
        self.requests: list[HttpRequest] = []

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("no fake response configured")
        return self._responses.pop(0)


def _tencent_line() -> bytes:
    values = [""] * 53
    values[0] = "51"
    values[1] = "贵州茅台"
    values[2] = "600519"
    values[3] = "1234.56"
    values[4] = "1200.00"
    values[5] = "1210.00"
    values[30] = "20260805150103"
    values[31] = "34.56"
    values[32] = "2.88"
    values[33] = "1240.00"
    values[34] = "1198.00"
    values[37] = "456789.01"
    values[38] = "1.23"
    values[39] = "22.34"
    values[43] = "3.50"
    values[44] = "12345.67"
    values[45] = "23456.78"
    values[46] = "5.67"
    values[47] = "1320.00"
    values[48] = "1080.00"
    values[49] = "1.45"
    values[52] = "20.01"
    payload = f'v_sh600519="{"~".join(values)}";'
    return payload.encode("gbk")


def test_tencent_quote_client_parses_public_quote_payload() -> None:
    transport = FakeTransport([HttpResponse(status_code=200, body=_tencent_line())])
    client = TencentQuoteClient(transport=transport)  # type: ignore[arg-type]

    rows = client.quote(["600519"])

    assert rows[0]["symbol"] == "600519"
    assert rows[0]["name"] == "贵州茅台"
    assert rows[0]["price"] == pytest.approx(1234.56)
    assert rows[0]["published_at"] == datetime(2026, 8, 5, 15, 1, 3, tzinfo=UTC)
    assert transport.requests[0].url.endswith("sh600519")


@pytest.mark.asyncio
async def test_tencent_quote_adapter_normalizes_market_record() -> None:
    transport = FakeTransport([HttpResponse(status_code=200, body=_tencent_line())])
    adapter = TencentQuoteAdapter(
        symbols=["600519"],
        client=TencentQuoteClient(transport=transport),  # type: ignore[arg-type]
    )

    batch = await adapter.fetch()

    assert len(batch.records) == 1
    record = batch.records[0]
    assert record.source.provider == "tencent-quote"
    assert record.source.type.value == "market"
    assert record.source.level.value == "market_data"
    assert record.external_id == "600519:20260805150103"
    assert record.content.startswith("贵州茅台(600519) 最新价 1234.56")
    assert record.metadata["published_at"] == "2026-08-05T15:01:03+00:00"


@pytest.mark.asyncio
async def test_cailianpress_adapter_maps_public_news_to_source_records() -> None:
    payload = {
        "data": {
            "roll_data": [
                {
                    "id": 1001,
                    "title": "财联社快讯",
                    "content": "这里是完整正文",
                    "ctime": 1785916800,
                }
            ]
        }
    }
    transport = FakeTransport(
        [HttpResponse(status_code=200, body=json.dumps(payload).encode("utf-8"))]
    )
    adapter = CailianpressTelegraphAdapter(
        client=CailianpressTelegraphClient(transport=transport),  # type: ignore[arg-type]
    )

    batch = await adapter.fetch()

    assert len(batch.records) == 1
    record = batch.records[0]
    assert record.source.provider == "cailianpress-telegraph"
    assert record.source.type.value == "news"
    assert record.title == "财联社快讯"
    assert record.content == "这里是完整正文"
    assert record.external_id == "1001"


@pytest.mark.asyncio
async def test_snowball_hot_posts_adapter_preserves_engagement_and_author_metadata() -> None:
    payload = [
        {
            "id": 9527,
            "title": "热门讨论",
            "description": "雪球热帖正文",
            "created_at": 1785916800000,
            "target": "/S/SH600519/9527",
            "like_count": 12,
            "reply_count": 5,
            "retweet_count": 3,
            "view_count": 1200,
            "user": {"screen_name": "研究员A", "id": 77, "followers_count": 888},
        }
    ]
    transport = FakeTransport(
        [HttpResponse(status_code=200, body=json.dumps(payload).encode("utf-8"))]
    )
    adapter = SnowballHotPostsAdapter(
        cookie="xq_a_token=test; u=1",
        client=SnowballClient(cookie="xq_a_token=test; u=1", transport=transport),  # type: ignore[arg-type]
    )

    batch = await adapter.fetch()

    assert len(batch.records) == 1
    record = batch.records[0]
    assert record.source.provider == "xueqiu-hot-posts"
    assert record.source.type.value == "social"
    assert record.engagement is not None
    assert record.engagement.likes == 12
    assert record.engagement.comments == 5
    assert record.metadata["author"] == "研究员A"
    assert str(record.url) == "https://xueqiu.com/S/SH600519/9527"
