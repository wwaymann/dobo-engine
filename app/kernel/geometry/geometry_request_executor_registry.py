"""
DOBO CAD Kernel

Geometry Request Executor Registry

Registers specialized GeometryRequest executors and
dispatches requests to the correct implementation.
"""

from __future__ import annotations

from kernel.contracts.geometry_operation_type import (
    GeometryOperationType,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
)
from kernel.contracts.geometry_result import (
    GeometryResult,
)

from .geometry_request_executor import (
    GeometryRequestExecutor,
)


class GeometryRequestExecutorRegistry:
    """
    Registry and dispatcher for specialized geometry
    request executors.

    One executor may be registered for each
    GeometryOperationType.
    """

    def __init__(self) -> None:
        self._executors: dict[
            GeometryOperationType,
            GeometryRequestExecutor,
        ] = {}

    def register(
        self,
        executor: GeometryRequestExecutor,
    ) -> None:
        """
        Registers one geometry executor.
        """

        if not isinstance(
            executor,
            GeometryRequestExecutor,
        ):
            raise TypeError(
                "GeometryRequestExecutorRegistry "
                "requires GeometryRequestExecutor."
            )

        operation = executor.operation_type

        if not isinstance(
            operation,
            GeometryOperationType,
        ):
            raise TypeError(
                "GeometryRequestExecutor "
                "operation_type must be "
                "GeometryOperationType."
            )

        if operation in self._executors:
            raise ValueError(
                "A GeometryRequestExecutor is already "
                f"registered for '{operation.value}'."
            )

        self._executors[
            operation
        ] = executor

    def unregister(
        self,
        operation: GeometryOperationType,
    ) -> GeometryRequestExecutor:
        """
        Removes and returns one registered executor.
        """

        self._validate_operation(
            operation
        )

        try:
            return self._executors.pop(
                operation
            )

        except KeyError as error:
            raise LookupError(
                "No GeometryRequestExecutor is "
                f"registered for '{operation.value}'."
            ) from error

    def get(
        self,
        operation: GeometryOperationType,
    ) -> GeometryRequestExecutor:
        """
        Returns the executor registered for an
        operation type.
        """

        self._validate_operation(
            operation
        )

        try:
            return self._executors[
                operation
            ]

        except KeyError as error:
            available = ", ".join(
                item.value
                for item in self._executors
            )

            raise LookupError(
                "No GeometryRequestExecutor is "
                f"registered for '{operation.value}'. "
                f"Available: {available or '<none>'}"
            ) from error

    def execute(
        self,
        request: GeometryRequest,
    ) -> GeometryResult:
        """
        Resolves and executes one GeometryRequest.
        """

        if not isinstance(
            request,
            GeometryRequest,
        ):
            raise TypeError(
                "GeometryRequestExecutorRegistry.execute "
                "requires GeometryRequest."
            )

        request.validate()

        executor = self.get(
            request.operation
        )

        if not executor.supports(
            request.operation
        ):
            raise RuntimeError(
                "Resolved GeometryRequestExecutor "
                "does not support the request."
            )

        result = executor.execute(
            request
        )

        if not isinstance(
            result,
            GeometryResult,
        ):
            raise TypeError(
                "GeometryRequestExecutor must return "
                "GeometryResult."
            )

        result.validate()

        return result

    def contains(
        self,
        operation: GeometryOperationType,
    ) -> bool:
        """
        Returns whether an executor is registered.
        """

        if not isinstance(
            operation,
            GeometryOperationType,
        ):
            return False

        return operation in self._executors

    def clear(self) -> None:
        """
        Removes every registered executor.
        """

        self._executors.clear()

    def validate(self) -> None:
        """
        Validates the complete registry.
        """

        for operation, executor in (
            self._executors.items()
        ):
            if not isinstance(
                operation,
                GeometryOperationType,
            ):
                raise TypeError(
                    "Registry contains an invalid "
                    "operation key."
                )

            if not isinstance(
                executor,
                GeometryRequestExecutor,
            ):
                raise TypeError(
                    "Registry contains an invalid "
                    "executor."
                )

            if executor.operation_type is not operation:
                raise ValueError(
                    "Registered executor operation_type "
                    "does not match its registry key."
                )

    @property
    def count(self) -> int:
        """
        Number of registered executors.
        """

        return len(
            self._executors
        )

    @property
    def operations(
        self,
    ) -> tuple[
        GeometryOperationType,
        ...,
    ]:
        """
        Registered geometry operation types.
        """

        return tuple(
            self._executors.keys()
        )

    @property
    def executors(
        self,
    ) -> tuple[
        GeometryRequestExecutor,
        ...,
    ]:
        """
        Registered executor instances.
        """

        return tuple(
            self._executors.values()
        )

    @staticmethod
    def _validate_operation(
        operation: GeometryOperationType,
    ) -> None:
        """
        Validates one operation identifier.
        """

        if not isinstance(
            operation,
            GeometryOperationType,
        ):
            raise TypeError(
                "operation must be "
                "GeometryOperationType."
            )