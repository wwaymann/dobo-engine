"""
DOBO CAD Kernel

Operation Dispatcher

Resolves the correct executor for each Kernel operation
and applies its payload to the shared execution context.
"""

from __future__ import annotations

from typing import Any, cast

from kernel.contracts.operations import KernelOperation
from kernel.core.execution_context import (
    KernelExecutionContext,
)
from kernel.core.operation_executor import (
    OperationExecutor,
    OperationExecutorPayload,
)


ExecutorType = OperationExecutor[Any]


class OperationDispatcher:
    """
    Registry and dispatcher for OperationExecutor objects.

    The dispatcher stores heterogeneous executors:
    GeometryOperationExecutor, BooleanOperationExecutor
    and ExportOperationExecutor.
    """

    def __init__(self) -> None:
        self._executors: dict[
            type[KernelOperation],
            ExecutorType,
        ] = {}

    def register(
        self,
        executor: ExecutorType,
    ) -> None:
        """
        Registers one executor by operation class.
        """

        if not isinstance(
            executor,
            OperationExecutor,
        ):
            raise TypeError(
                "OperationDispatcher accepts "
                "OperationExecutor instances only."
            )

        operation_class = cast(
            type[KernelOperation],
            executor.operation_class,
        )

        if not isinstance(
            operation_class,
            type,
        ):
            raise TypeError(
                "OperationExecutor operation_class "
                "must be a class."
            )

        existing = self._executors.get(
            operation_class
        )

        if (
            existing is not None
            and existing is not executor
        ):
            raise ValueError(
                "OperationDispatcher already contains "
                f"an executor for {operation_class.__name__}."
            )

        self._executors[
            operation_class
        ] = executor

    def unregister(
        self,
        operation_class: type[KernelOperation],
    ) -> ExecutorType:
        """
        Removes and returns one registered executor.
        """

        try:
            return self._executors.pop(
                operation_class
            )

        except KeyError as error:
            raise KeyError(
                "OperationDispatcher does not contain "
                f"an executor for {operation_class.__name__}."
            ) from error

    def resolve(
        self,
        operation: KernelOperation,
    ) -> ExecutorType:
        """
        Resolves an executor by exact operation class
        first and compatible subclass second.
        """

        exact = self._executors.get(
            type(
                operation
            )
        )

        if exact is not None:
            return exact

        for executor in self._executors.values():
            if executor.supports(
                operation
            ):
                return executor

        available = ", ".join(
            operation_class.__name__
            for operation_class
            in self._executors
        )

        raise KeyError(
            "OperationDispatcher has no executor for "
            f"{type(operation).__name__}. "
            f"Available: {available or '<none>'}"
        )

    def dispatch(
        self,
        operation: KernelOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """
        Executes one operation and applies its payload
        to the shared context.
        """

        operation.validate()
        context.validate()

        executor = self.resolve(
            operation
        )

        context.begin_operation(
            operation
        )

        try:
            payload = executor.execute(
                operation,
                context,
            )

            self._apply_payload(
                payload=payload,
                context=context,
                operation=operation,
            )

        except Exception as error:
            context.log(
                level="error",
                message=str(
                    error
                ),
                operation_id=operation.id,
                metadata={
                    "exception_type": (
                        type(
                            error
                        ).__name__
                    ),
                },
            )

            context.active_operation_id = None

            raise

        context.end_operation(
            operation
        )

        return payload

    def validate(self) -> None:
        """
        Validates all registered executors.
        """

        for operation_class, executor in (
            self._executors.items()
        ):
            if not isinstance(
                operation_class,
                type,
            ):
                raise TypeError(
                    "OperationDispatcher contains "
                    "an invalid operation key."
                )

            if not isinstance(
                executor,
                OperationExecutor,
            ):
                raise TypeError(
                    "OperationDispatcher contains "
                    "an invalid executor."
                )

            registered_class = cast(
                type[KernelOperation],
                executor.operation_class,
            )

            if registered_class is not operation_class:
                raise ValueError(
                    "OperationDispatcher executor key "
                    "does not match operation_class."
                )

    @property
    def count(self) -> int:
        """
        Returns the number of registered executors.
        """

        return len(
            self._executors
        )

    @property
    def operation_classes(
        self,
    ) -> tuple[type[KernelOperation], ...]:
        """
        Returns supported operation classes.
        """

        return tuple(
            self._executors.keys()
        )

    @staticmethod
    def _apply_payload(
        *,
        payload: OperationExecutorPayload,
        context: KernelExecutionContext,
        operation: KernelOperation,
    ) -> None:
        """
        Commits one validated executor payload.
        """

        payload.validate()

        if payload.solid is not None:
            if payload.output_id is None:
                raise RuntimeError(
                    "Solid payload requires output_id."
                )

            context.solids.register(
                payload.output_id,
                payload.solid,
            )

        if payload.export_path is not None:
            context.add_export(
                payload.export_path
            )

        for warning in payload.warnings:
            context.add_warning(
                warning,
                operation_id=operation.id,
            )

        if payload.metadata:
            context.log(
                level="debug",
                message=(
                    "Operation payload committed."
                ),
                operation_id=operation.id,
                metadata=payload.metadata,
            )