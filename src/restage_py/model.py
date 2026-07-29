from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Callable, Iterable, Mapping


class NodeKind(str, Enum):
    REQUEST = "Request"
    RESPONSE = "Response"
    RUNNER = "Runner"
    CALL = "Call"


@dataclass(frozen=True, slots=True)
class NodeMetadata:
    kind: NodeKind
    function_name: str
    identifier: str | None = None
    namespace: str = ""
    folder: str = ""
    request: str = ""
    depends_on: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    verify: int | None = None
    soft: bool = False
    log: str = "none"

    @property
    def canonical_reference(self) -> str:
        return f"#{self.identifier}" if self.identifier else self.function_name


@dataclass(slots=True)
class RequestSpec:
    name: str
    method: str
    url: str
    namespace: str = ""
    folder: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    query: dict[str, str] = field(default_factory=dict)
    body: Any = None

    def copy(self) -> "RequestSpec":
        return replace(
            self,
            headers=dict(self.headers),
            query=dict(self.query),
        )


@dataclass(slots=True)
class HttpResponse:
    status_code: int
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionRecord:
    metadata: NodeMetadata
    response: HttpResponse | None
    value: Any = None


NodeFunction = Callable[..., Any]


class Collection:
    """In-memory collection keyed by namespace, folder, and request name."""

    def __init__(self, requests: Iterable[RequestSpec] = ()) -> None:
        self._requests: dict[tuple[str, str, str], RequestSpec] = {}
        for request in requests:
            self.add(request)

    def add(self, request: RequestSpec) -> "Collection":
        key = (request.namespace, request.folder, request.name)
        self._requests[key] = request
        return self

    def get(self, namespace: str, folder: str, name: str) -> RequestSpec:
        key = (namespace, folder, name)
        try:
            return self._requests[key].copy()
        except KeyError as exc:
            raise KeyError(
                f'Request not found: "{name}" '
                f"(namespace={namespace}, folder={folder})"
            ) from exc

    def as_mapping(self) -> Mapping[tuple[str, str, str], RequestSpec]:
        return dict(self._requests)
