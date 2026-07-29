from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

from .assertions import ReStageAssert
from .errors import DependencyCycleError, RegistrationError, ResolutionError, VerificationError
from .executors import Executor
from .model import (
    Collection,
    ExecutionRecord,
    HttpResponse,
    NodeFunction,
    NodeKind,
    NodeMetadata,
    RequestSpec,
)


@dataclass(slots=True)
class InvocationContext:
    metadata: NodeMetadata
    request: RequestSpec | None
    response: HttpResponse | None
    variables: dict[str, Any]
    records: dict[str, ExecutionRecord]
    asserts: ReStageAssert = field(init=False)

    def __post_init__(self) -> None:
        self.asserts = ReStageAssert(self.response)

    def dependency(self, reference: str) -> ExecutionRecord:
        normalized = reference[1:] if reference.startswith("#") else reference
        try:
            return self.records[normalized]
        except KeyError as exc:
            raise ResolutionError(f"Dependency result not found: {reference}") from exc


@dataclass(frozen=True, slots=True)
class RegisteredNode:
    metadata: NodeMetadata
    function: NodeFunction


class Registry:
    def __init__(self) -> None:
        self._by_name: dict[str, RegisteredNode] = {}
        self._by_id: dict[str, RegisteredNode] = {}

    def register(self, metadata: NodeMetadata, function: NodeFunction) -> None:
        if metadata.function_name in self._by_name:
            raise RegistrationError(f"Function already registered: {metadata.function_name}")
        if metadata.identifier and metadata.identifier in self._by_id:
            raise RegistrationError(f"Duplicate ReStage id: {metadata.identifier}")
        node = RegisteredNode(metadata=metadata, function=function)
        self._by_name[metadata.function_name] = node
        if metadata.identifier:
            self._by_id[metadata.identifier] = node

    def resolve(self, reference: str) -> RegisteredNode:
        if reference.startswith("#"):
            key = reference[1:]
            node = self._by_id.get(key)
        else:
            node = self._by_name.get(reference) or self._by_id.get(reference)
        if node is None:
            raise ResolutionError(f"ReStage node not found: {reference}")
        return node

    def nodes(self) -> tuple[RegisteredNode, ...]:
        return tuple(self._by_name.values())


class Runtime:
    def __init__(
        self,
        registry: Registry,
        collection: Collection,
        executor: Executor,
        *,
        session: bool = True,
    ) -> None:
        self.registry = registry
        self.collection = collection
        self.executor = executor
        self.session = session
        self.variables: dict[str, Any] = {}
        self.records: dict[str, ExecutionRecord] = {}
        self.execution_order: list[str] = []
        self._state: dict[str, str] = {}

    def run(self, reference: str) -> ExecutionRecord:
        if not self.session:
            self.records.clear()
            self.execution_order.clear()
            self._state.clear()
        return self._execute(self.registry.resolve(reference))

    def reset(self) -> None:
        self.variables.clear()
        self.records.clear()
        self.execution_order.clear()
        self._state.clear()

    def _execute(self, node: RegisteredNode) -> ExecutionRecord:
        key = self._record_key(node.metadata)
        state = self._state.get(key)
        if state == "done":
            return self.records[key]
        if state == "visiting":
            raise DependencyCycleError(
                f"Dependency cycle detected while resolving {node.metadata.canonical_reference}"
            )

        self._state[key] = "visiting"
        dependency_records: list[ExecutionRecord] = []
        for dependency in node.metadata.depends_on:
            dependency_records.append(self._execute(self.registry.resolve(dependency)))

        namespace, folder = self._resolve_scope(node.metadata)
        request = self._resolve_request(node.metadata, namespace, folder)
        response: HttpResponse | None = None
        value: Any = None

        if node.metadata.kind is NodeKind.REQUEST:
            context = InvocationContext(
                metadata=node.metadata,
                request=request,
                response=None,
                variables=self.variables,
                records=self.records,
            )
            value = self._invoke(node.function, context)
            if context.request is None:
                raise ResolutionError(
                    f"@ReStage.Request {node.metadata.function_name} has no request to execute."
                )
            response = self.executor.execute(context.request)
        else:
            if request is not None:
                response = self.executor.execute(request)
            elif dependency_records:
                response = dependency_records[-1].response

            if node.metadata.verify is not None and not node.metadata.soft:
                self._verify_status(node.metadata, response)

            context = InvocationContext(
                metadata=node.metadata,
                request=request,
                response=response,
                variables=self.variables,
                records=self.records,
            )
            value = self._invoke(node.function, context)

            if node.metadata.verify is not None and node.metadata.soft:
                self._verify_status(node.metadata, response)
            context.asserts.verify()

        record = ExecutionRecord(metadata=node.metadata, response=response, value=value)
        self.records[key] = record
        if node.metadata.identifier:
            self.records[node.metadata.identifier] = record
        self.records[node.metadata.function_name] = record
        self.execution_order.append(node.metadata.canonical_reference)
        self._state[key] = "done"
        return record

    def _resolve_scope(self, metadata: NodeMetadata) -> tuple[str, str]:
        namespace = metadata.namespace
        folder = metadata.folder
        if namespace and folder:
            return namespace, folder

        for dependency_ref in metadata.depends_on:
            dependency = self.registry.resolve(dependency_ref).metadata
            inherited_namespace, inherited_folder = self._resolve_scope(dependency)
            namespace = namespace or inherited_namespace
            folder = folder or inherited_folder
            if namespace and folder:
                break
        return namespace, folder

    def _resolve_request(
        self,
        metadata: NodeMetadata,
        namespace: str,
        folder: str,
    ) -> RequestSpec | None:
        if not metadata.request:
            return None
        try:
            return self.collection.get(namespace, folder, metadata.request)
        except KeyError as exc:
            raise ResolutionError(str(exc)) from exc

    @staticmethod
    def _verify_status(metadata: NodeMetadata, response: HttpResponse | None) -> None:
        actual = response.status_code if response else None
        if actual != metadata.verify:
            raise VerificationError(
                f"(@ReStage.{metadata.kind.value}: method={metadata.function_name}, "
                f"namespace={metadata.namespace}, folder={metadata.folder}, "
                f"request={metadata.request}) Expected status code "
                f"{metadata.verify}, but received {actual}."
            )

    @staticmethod
    def _invoke(function: NodeFunction, context: InvocationContext) -> Any:
        signature = inspect.signature(function)
        parameters = list(signature.parameters.values())
        if not parameters:
            return function()
        if len(parameters) == 1:
            return function(context)
        raise TypeError(
            f"{function.__name__} must accept zero parameters or one InvocationContext parameter."
        )

    @staticmethod
    def _record_key(metadata: NodeMetadata) -> str:
        return metadata.identifier or metadata.function_name
