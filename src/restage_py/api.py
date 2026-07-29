from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from .executors import Executor
from .model import Collection, NodeKind, NodeMetadata
from .runtime import Registry, Runtime

F = TypeVar("F", bound=Callable[..., Any])


class ReStage:
    """Decorator facade and runtime factory."""

    def __init__(self) -> None:
        self.registry = Registry()

    def request(self, **options: Any) -> Callable[[F], F]:
        return self._decorator(NodeKind.REQUEST, **options)

    def response(self, **options: Any) -> Callable[[F], F]:
        return self._decorator(NodeKind.RESPONSE, **options)

    def runner(self, **options: Any) -> Callable[[F], F]:
        return self._decorator(NodeKind.RUNNER, **options)

    def call(self, **options: Any) -> Callable[[F], F]:
        return self._decorator(NodeKind.CALL, **options)

    def runtime(
        self,
        collection: Collection,
        executor: Executor,
        *,
        session: bool = True,
    ) -> Runtime:
        return Runtime(
            registry=self.registry,
            collection=collection,
            executor=executor,
            session=session,
        )

    def _decorator(
        self,
        kind: NodeKind,
        *,
        id: str | None = None,
        namespace: str = "",
        folder: str = "",
        request: str = "",
        depends_on: str | Iterable[str] | None = None,
        tags: str | Iterable[str] | None = None,
        verify: int | None = None,
        soft: bool = False,
        log: str = "none",
    ) -> Callable[[F], F]:
        dependencies = _normalize_many(depends_on)
        normalized_tags = _normalize_many(tags)

        def decorate(function: F) -> F:
            metadata = NodeMetadata(
                kind=kind,
                function_name=function.__name__,
                identifier=id,
                namespace=namespace,
                folder=folder,
                request=request,
                depends_on=dependencies,
                tags=normalized_tags,
                verify=verify,
                soft=soft,
                log=log,
            )
            setattr(function, "__restage__", metadata)
            self.registry.register(metadata, function)
            return function

        return decorate


def _normalize_many(value: str | Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)
