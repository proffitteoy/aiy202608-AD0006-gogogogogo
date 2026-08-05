from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TextIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .models import SourceRecord


class DeliveryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DeliveryReceipt:
    external_id: str
    status_code: int | None
    duplicate: bool = False


@dataclass(frozen=True, slots=True)
class TransportResponse:
    status_code: int
    body: bytes = b""


class RecordSink(Protocol):
    async def send(
        self,
        record: SourceRecord,
        *,
        replay_at: datetime,
        scenario_id: str,
        sequence: int,
    ) -> DeliveryReceipt: ...


Transport = Callable[[str, bytes, float, str], TransportResponse | int]


class HttpIngestionSink:
    def __init__(
        self,
        endpoint: str,
        *,
        timeout_seconds: float = 10.0,
        max_attempts: int = 3,
        backoff_seconds: float = 0.25,
        transport: Transport | None = None,
    ) -> None:
        parts = urlsplit(endpoint)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("ingestion endpoint must be an absolute HTTP(S) URL")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds must not be negative")
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.transport = transport or _post_json

    async def send(
        self,
        record: SourceRecord,
        *,
        replay_at: datetime,
        scenario_id: str,
        sequence: int,
    ) -> DeliveryReceipt:
        payload = record.to_ingestion_payload(
            replay_at=replay_at,
            scenario_id=scenario_id,
            sequence=sequence,
        )
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = await asyncio.to_thread(
                    self.transport,
                    self.endpoint,
                    body,
                    self.timeout_seconds,
                    record.external_id,
                )
                if isinstance(response, int):
                    response = TransportResponse(response)
                status_code = response.status_code
                if 200 <= status_code < 300:
                    return DeliveryReceipt(
                        record.external_id,
                        status_code,
                        duplicate=_is_duplicate_response(response.body),
                    )
                if status_code < 500 and status_code != 429:
                    raise DeliveryError(
                        f"ingestion rejected {record.external_id} with HTTP {status_code}"
                    )
                last_error = DeliveryError(
                    f"ingestion failed for {record.external_id} with HTTP {status_code}"
                )
            except DeliveryError:
                raise
            except (HTTPError, URLError, OSError) as error:
                if isinstance(error, HTTPError) and error.code < 500 and error.code != 429:
                    raise DeliveryError(
                        f"ingestion rejected {record.external_id} with HTTP {error.code}"
                    ) from error
                last_error = error

            if attempt < self.max_attempts:
                await asyncio.sleep(self.backoff_seconds * (2 ** (attempt - 1)))

        raise DeliveryError(
            f"ingestion unavailable after {self.max_attempts} attempts for "
            f"{record.external_id}: {last_error}"
        ) from last_error


class JsonLineSink:
    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream or sys.stdout

    async def send(
        self,
        record: SourceRecord,
        *,
        replay_at: datetime,
        scenario_id: str,
        sequence: int,
    ) -> DeliveryReceipt:
        payload = record.to_ingestion_payload(
            replay_at=replay_at,
            scenario_id=scenario_id,
            sequence=sequence,
        )
        self.stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        self.stream.flush()
        return DeliveryReceipt(record.external_id, None)


def _post_json(
    endpoint: str,
    body: bytes,
    timeout_seconds: float,
    idempotency_key: str,
) -> TransportResponse:
    request = Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Idempotency-Key": idempotency_key,
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return TransportResponse(status_code=response.status, body=response.read())


def _is_duplicate_response(body: bytes) -> bool:
    if not body:
        return False
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("outcome") == "duplicate"
