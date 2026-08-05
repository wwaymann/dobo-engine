"""DOBO CAD Kernel - operation executor abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, cast

from kernel.contracts.operations import KernelOperation
from kernel.contracts.solid import Solid
from kernel.core.execution_context import KernelExecutionContext


OperationT = TypeVar("OperationT", bound=KernelOperation)


@dataclass(frozen=True, slots=True)
class OperationExecutorPayload:
    """Neutral payload returned by a concrete operation executor."""

    output_id: str | None = None
    solid: Solid | None = None
    export_path: str | None = None
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.output_id is not None and (
            not isinstance(self.output_id, str) or not self.output_id.strip()
        ):
            raise ValueError("OperationExecutorPayload output_id must be non-empty.")
        if self.solid is not None:
            self.solid.validate()
            if self.output_id is None:
                raise ValueError("A Solid payload requires output_id.")
        if self.output_id is not None and self.solid is None:
            raise ValueError("output_id requires a Solid.")
        if self.export_path is not None and (
            not isinstance(self.export_path, str) or not self.export_path.strip()
        ):
            raise ValueError("export_path must be non-empty.")
        for warning in self.warnings:
            if not isinstance(warning, str) or not warning.strip():
                raise ValueError("warnings must contain non-empty strings.")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")


class OperationExecutor(ABC, Generic[OperationT]):
    """Base class for concrete Geometry, Boolean and Export executors."""

    @property
    @abstractmethod
    def operation_class(self) -> type[OperationT]:
        """Operation class supported by this executor."""

    def supports(self, operation: KernelOperation) -> bool:
        return isinstance(operation, self.operation_class)

    def execute(
        self,
        operation: KernelOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        if not self.supports(operation):
            raise TypeError(
                f"{type(self).__name__} cannot execute {type(operation).__name__}."
            )
        if not isinstance(context, KernelExecutionContext):
            raise TypeError("OperationExecutor requires KernelExecutionContext.")
        typed_operation = cast(OperationT, operation)
        payload = self._execute(typed_operation, context)
        if not isinstance(payload, OperationExecutorPayload):
            raise TypeError("Executors must return OperationExecutorPayload.")
        payload.validate()
        return payload

    @abstractmethod
    def _execute(
        self,
        operation: OperationT,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """Performs the concrete operation."""