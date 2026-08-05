"""
DOBO CAD Kernel

Operation Executor

Defines the common interface implemented by every
Kernel operation executor.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Generic
from typing import TypeVar

from kernel.contracts.operations import (
    KernelOperation,
)
from kernel.contracts.solid import (
    Solid,
)
from kernel.core.execution_context import (
    KernelExecutionContext,
)


OperationT = TypeVar(
    "OperationT",
    bound=KernelOperation,
)


@dataclass(
    frozen=True,
    slots=True,
)
class OperationExecutorPayload:
    """
    Neutral payload returned by every executor.

    Geometry executors return:

        output_id
        solid

    Boolean executors return:

        output_id
        solid

    Export executors return:

        export_path
    """

    output_id: str | None = None

    solid: Solid | None = None

    export_path: str | None = None

    warnings: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    def validate(self) -> None:
        """
        Validates the payload.
        """

        if self.output_id is not None:
            if (
                not isinstance(
                    self.output_id,
                    str,
                )
                or not self.output_id.strip()
            ):
                raise ValueError(
                    "OperationExecutorPayload "
                    "output_id must be a non-empty string."
                )

        if self.solid is not None:
            self.solid.validate()

            if self.output_id is None:
                raise ValueError(
                    "A payload containing a Solid "
                    "must also define output_id."
                )

        if (
            self.output_id is not None
            and self.solid is None
        ):
            raise ValueError(
                "output_id requires a Solid."
            )

        if self.export_path is not None:
            if (
                not isinstance(
                    self.export_path,
                    str,
                )
                or not self.export_path.strip()
            ):
                raise ValueError(
                    "export_path must be "
                    "a non-empty string."
                )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple."
            )

        for warning in self.warnings:
            if (
                not isinstance(
                    warning,
                    str,
                )
                or not warning.strip()
            ):
                raise ValueError(
                    "warnings must contain "
                    "non-empty strings."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be a dictionary."
            )

    @property
    def produced_solid(
        self,
    ) -> bool:
        """
        Returns whether this payload
        generated a Solid.
        """

        return self.solid is not None

    @property
    def produced_export(
        self,
    ) -> bool:
        """
        Returns whether this payload
        generated an exported file.
        """

        return self.export_path is not None


class OperationExecutor(
    ABC,
    Generic[OperationT],
):
    """
    Base class implemented by all
    Kernel executors.
    """

    @property
    @abstractmethod
    def operation_class(
        self,
    ) -> type[OperationT]:
        """
        Returns the operation type supported
        by this executor.
        """

    def supports(
        self,
        operation: KernelOperation,
    ) -> bool:
        """
        Returns whether this executor supports
        the supplied operation.
        """

        return isinstance(
            operation,
            self.operation_class,
        )

    def execute(
        self,
        operation: KernelOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """
        Executes one operation.
        """

        if not self.supports(
            operation,
        ):
            raise TypeError(
                f"{type(self).__name__} "
                f"cannot execute "
                f"{type(operation).__name__}."
            )

        if not isinstance(
            context,
            KernelExecutionContext,
        ):
            raise TypeError(
                "context must be "
                "KernelExecutionContext."
            )

        payload = self._execute(
            operation,  # type: ignore[arg-type]
            context,
        )

        if not isinstance(
            payload,
            OperationExecutorPayload,
        ):
            raise TypeError(
                "Executors must return "
                "OperationExecutorPayload."
            )

        payload.validate()

        return payload

    @abstractmethod
    def _execute(
        self,
        operation: OperationT,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """
        Executes the concrete operation.
        """