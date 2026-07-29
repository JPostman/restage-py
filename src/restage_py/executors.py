from __future__ import annotations

import json
from typing import Callable, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .model import HttpResponse, RequestSpec


class Executor(Protocol):
    def execute(self, request: RequestSpec) -> HttpResponse:
        ...


class MockExecutor:
    """Executor backed by a user-supplied callable; ideal for tests and demos."""

    def __init__(self, handler: Callable[[RequestSpec], HttpResponse]) -> None:
        self._handler = handler
        self.calls: list[RequestSpec] = []

    def execute(self, request: RequestSpec) -> HttpResponse:
        copied = request.copy()
        self.calls.append(copied)
        return self._handler(copied)


class UrllibExecutor:
    """Small standard-library HTTP executor for prototype use."""

    def execute(self, request: RequestSpec) -> HttpResponse:
        url = request.url
        if request.query:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(request.query)}"

        data = None
        headers = dict(request.headers)
        if request.body is not None:
            data = json.dumps(request.body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        native_request = Request(
            url=url,
            data=data,
            headers=headers,
            method=request.method.upper(),
        )
        with urlopen(native_request) as response:  # nosec: prototype caller controls URL
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                body = json.loads(raw.decode("utf-8"))
            else:
                body = raw.decode("utf-8", errors="replace")
            return HttpResponse(
                status_code=response.status,
                body=body,
                headers=dict(response.headers.items()),
            )
