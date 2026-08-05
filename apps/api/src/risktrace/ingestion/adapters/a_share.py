from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from risktrace.ingestion.adapters.base import (
    AdapterHealth,
    filter_time_range,
    iso_cursor,
    merge_metadata,
    timed_call,
    utc_now,
)
from risktrace.ingestion.adapters.http import HttpRequest, HttpTransport, decode_json, decode_text
from risktrace.ingestion.schemas import FetchBatch, SourceDescriptor, SourceRecord

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)
_SH_INDEX = {"000300", "000905", "000016", "000688", "000852", "000010"}


def _get_prefix(code: str) -> str:
    normalized = code.lower()
    if normalized.startswith(("sh", "sz", "bj")):
        return normalized
    if code.startswith("92"):
        return f"bj{code}"
    if code in _SH_INDEX or code.startswith(("5", "6", "9")):
        return f"sh{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return f"sz{code}"


def _parse_tencent_timestamp(value: str, fallback: datetime) -> datetime:
    if value:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    return fallback


class TencentQuoteClient:
    def __init__(
        self,
        transport: HttpTransport | None = None,
    ) -> None:
        self.transport = transport or HttpTransport()

    def quote(self, symbols: list[str]) -> list[dict[str, Any]]:
        prefixed = [_get_prefix(symbol) for symbol in symbols]
        key_of = dict(zip(prefixed, symbols, strict=True))
        request = HttpRequest(
            method="GET",
            url="https://qt.gtimg.cn/q=" + ",".join(prefixed),
            headers={"User-Agent": _UA},
        )
        raw = decode_text(self.transport.send(request), encoding="gbk")
        rows: list[dict[str, Any]] = []
        for line in raw.strip().split(";"):
            if "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            values = line.split('"')[1].split("~")
            if len(values) < 53:
                continue
            symbol = key_of.get(key, key[2:])
            amount_wan = float(values[37]) if values[37] else 0.0
            price = float(values[3]) if values[3] else 0.0
            last_close = float(values[4]) if values[4] else 0.0
            is_stale = amount_wan == 0.0 and price == last_close and price > 0.0
            row: dict[str, Any] = {
                "symbol": symbol,
                "market_symbol": key,
                "name": values[1],
                "price": price,
                "last_close": last_close,
                "open": float(values[5]) if values[5] else 0.0,
                "change_amt": float(values[31]) if values[31] else 0.0,
                "change_pct": float(values[32]) if values[32] else 0.0,
                "high": float(values[33]) if values[33] else 0.0,
                "low": float(values[34]) if values[34] else 0.0,
                "amount_wan": amount_wan,
                "turnover_pct": float(values[38]) if values[38] else 0.0,
                "pe_ttm": float(values[39]) if values[39] else 0.0,
                "amplitude_pct": float(values[43]) if values[43] else 0.0,
                "float_mcap_yi": float(values[44]) if values[44] else 0.0,
                "mcap_yi": float(values[45]) if values[45] else 0.0,
                "pb": float(values[46]) if values[46] else 0.0,
                "limit_up": float(values[47]) if values[47] else 0.0,
                "limit_down": float(values[48]) if values[48] else 0.0,
                "vol_ratio": float(values[49]) if values[49] else 0.0,
                "pe_static": float(values[52]) if values[52] else 0.0,
                "quote_time": values[30],
                "published_at": _parse_tencent_timestamp(values[30], utc_now()),
                "is_stale": is_stale,
            }
            if is_stale and key[2:4] in {"43", "83", "87"}:
                row["stale_reason"] = "legacy_bse_code"
            elif is_stale:
                row["stale_reason"] = "zero_turnover_or_suspended"
            rows.append(row)
        return rows


class CailianpressTelegraphClient:
    def __init__(self, transport: HttpTransport | None = None) -> None:
        self.transport = transport or HttpTransport()

    def latest(self, *, page_size: int = 20) -> list[dict[str, Any]]:
        params = {
            "appName": "CailianpressWeb",
            "os": "web",
            "sv": "7.7.5",
            "last_time": "",
            "refresh_type": "1",
            "rn": str(page_size),
        }
        query = "&".join(f"{key}={params[key]}" for key in sorted(params))
        digest = hashlib.sha1(query.encode("utf-8")).hexdigest()
        sign = hashlib.md5(digest.encode("utf-8")).hexdigest()
        request = HttpRequest(
            method="GET",
            url="https://www.cls.cn/v1/roll/get_roll_list",
            params={**params, "sign": sign},
            headers={"User-Agent": _UA, "Referer": "https://www.cls.cn/"},
        )
        payload = decode_json(self.transport.send(request))
        if not isinstance(payload, dict):
            raise ValueError("unexpected cls payload")
        rows: list[dict[str, Any]] = []
        for item in payload.get("data", {}).get("roll_data", []) or []:
            if not isinstance(item, dict):
                continue
            ts = item.get("ctime")
            published_at = (
                datetime.fromtimestamp(ts, tz=UTC)
                if isinstance(ts, int | float)
                else utc_now()
            )
            title = item.get("title") or item.get("brief") or ""
            content = item.get("content") or item.get("brief") or title
            item_id = item.get("id")
            if not item_id:
                raw_identity = f"{title}|{published_at.isoformat()}|{content}"
                item_id = hashlib.sha256(raw_identity.encode("utf-8")).hexdigest()[:24]
            rows.append(
                {
                    "id": str(item_id),
                    "title": str(title),
                    "content": str(content),
                    "published_at": published_at,
                    "raw_item": item,
                }
            )
        return rows


class TencentQuoteAdapter:
    def __init__(
        self,
        *,
        symbols: list[str],
        stream: str = "a-share-live",
        collection_method: str = "public_http_api",
        license_scope: str = "internal_research",
        client: TencentQuoteClient | None = None,
    ) -> None:
        self.symbols = symbols
        self.client = client or TencentQuoteClient()
        self._descriptor = SourceDescriptor(
            provider="tencent-quote",
            stream=stream,
            type="market",
            level="market_data",
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
        fetched_at = utc_now()
        rows = filter_time_range(
            self.client.quote(self.symbols),
            timestamp_key="published_at",
            start_time=start_time,
            end_time=end_time,
        )
        records = tuple(self._to_record(row, fetched_at=fetched_at) for row in rows)
        return FetchBatch(records=records, next_cursor=iso_cursor(fetched_at))

    async def healthcheck(self) -> AdapterHealth:
        _, latency_ms = timed_call(lambda: self.client.quote(self.symbols[:1]))
        return AdapterHealth(
            status="healthy",
            checked_at=utc_now(),
            detail="public_tencent_quote_ok",
            latency_ms=latency_ms,
        )

    def _to_record(self, row: dict[str, Any], *, fetched_at: datetime) -> SourceRecord:
        symbol = str(row["symbol"])
        name = str(row["name"])
        price = float(row["price"])
        summary = (
            f"{name}({symbol}) 最新价 {price:.2f}，涨跌幅 {float(row['change_pct']):.2f}% ，"
            f"市值 {float(row['mcap_yi']):.2f} 亿。"
        )
        metadata = merge_metadata(
            {
                "symbol": symbol,
                "market_symbol": row["market_symbol"],
                "name": name,
                "price": price,
                "last_close": row["last_close"],
                "open": row["open"],
                "change_amt": row["change_amt"],
                "change_pct": row["change_pct"],
                "high": row["high"],
                "low": row["low"],
                "amount_wan": row["amount_wan"],
                "turnover_pct": row["turnover_pct"],
                "pe_ttm": row["pe_ttm"],
                "amplitude_pct": row["amplitude_pct"],
                "float_mcap_yi": row["float_mcap_yi"],
                "mcap_yi": row["mcap_yi"],
                "pb": row["pb"],
                "limit_up": row["limit_up"],
                "limit_down": row["limit_down"],
                "vol_ratio": row["vol_ratio"],
                "pe_static": row["pe_static"],
                "quote_time": row["quote_time"],
                "published_at": row["published_at"].isoformat(),
                "is_stale": row["is_stale"],
                "stale_reason": row.get("stale_reason"),
            },
            adapter_name="tencent_quote",
            extra={"fetched_at": fetched_at.isoformat()},
        )
        return SourceRecord.model_validate(
            {
                "external_id": f"{symbol}:{row['quote_time'] or iso_cursor(fetched_at)}",
                "source": self.descriptor.model_dump(),
                "published_at": row["published_at"],
                "collected_at": fetched_at,
                "title": f"{name} 行情快照",
                "content": summary,
                "url": f"https://gu.qq.com/{symbol.lower()}",
                "language": "zh-CN",
                "metadata": metadata,
                "raw_payload_ref": f"tencent-quote:{row['market_symbol']}",
            }
        )


class CailianpressTelegraphAdapter:
    def __init__(
        self,
        *,
        page_size: int = 20,
        stream: str = "cls-telegraph",
        collection_method: str = "public_http_api",
        license_scope: str = "internal_research",
        client: CailianpressTelegraphClient | None = None,
    ) -> None:
        self.page_size = page_size
        self.client = client or CailianpressTelegraphClient()
        self._descriptor = SourceDescriptor(
            provider="cailianpress-telegraph",
            stream=stream,
            type="news",
            level="professional_media",
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
        collected_at = utc_now()
        rows = filter_time_range(
            self.client.latest(page_size=self.page_size),
            timestamp_key="published_at",
            start_time=start_time,
            end_time=end_time,
        )
        records = tuple(self._to_record(row, collected_at=collected_at) for row in rows)
        return FetchBatch(records=records, next_cursor=iso_cursor(collected_at))

    async def healthcheck(self) -> AdapterHealth:
        _, latency_ms = timed_call(lambda: self.client.latest(page_size=1))
        return AdapterHealth(
            status="healthy",
            checked_at=utc_now(),
            detail="public_cls_telegraph_ok",
            latency_ms=latency_ms,
        )

    def _to_record(self, row: dict[str, Any], *, collected_at: datetime) -> SourceRecord:
        metadata = merge_metadata(
            {"source_id": row["id"]},
            adapter_name="cls_telegraph",
            extra={"raw_item": json.dumps(row["raw_item"], ensure_ascii=False)},
        )
        return SourceRecord.model_validate(
            {
                "external_id": row["id"],
                "source": self.descriptor.model_dump(),
                "published_at": row["published_at"],
                "collected_at": collected_at,
                "title": row["title"],
                "content": row["content"],
                "language": "zh-CN",
                "metadata": metadata,
                "raw_payload_ref": f"cls-telegraph:{row['id']}",
            }
        )
