from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    url: str
    params: Mapping[str, str] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes | None = None


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    body: bytes
    content_type: str | None = None


class HttpTransport:
    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def send(self, request: HttpRequest) -> HttpResponse:
        url = request.url
        if request.params:
            url = f"{url}?{urlencode(request.params)}"
        raw_request = Request(
            url=url,
            data=request.body,
            headers=dict(request.headers),
            method=request.method,
        )
        with urlopen(raw_request, timeout=self.timeout_seconds) as response:
            return HttpResponse(
                status_code=response.status,
                body=response.read(),
                content_type=response.headers.get("Content-Type"),
            )


def decode_json(response: HttpResponse) -> object:
    return json.loads(response.body.decode("utf-8"))


def decode_text(response: HttpResponse, *, encoding: str = "utf-8") -> str:
    return response.body.decode(encoding)
