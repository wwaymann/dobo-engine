"""
DOBO CAD Kernel

Geometry Operation Executor

Executes GeometryOperation objects through the
GeometryExecutionService.
"""

from __future__ import annotations

from kernel.contracts.operations import (
    GeometryOperation,
)
from kernel.core.execution_context import (
    KernelExecutionContext,
)
from kernel.core.operation_executor import (
    OperationExecutor,
    OperationExecutorPayload,
)
from kernel.services.geometry_execution_service import (
    GeometryExecutionService,
)


class GeometryOperationExecutor(
    OperationExecutor[GeometryOperation],
):
    """
    Executes GeometryOperation objects.

    Geometry generation is delegated completely to
    GeometryExecutionService.
    """

    def __init__(
        self,
        geometry_service: GeometryExecutionService,
    ) -> None:
        if not isinstance(
            geometry_service,
            GeometryExecutionService,
        ):
            raise TypeError(
                "GeometryOperationExecutor requires "
                "GeometryExecutionService."
            )

        self._geometry_service = geometry_service

    @property
    def operation_class(
        self,
    ) -> type[GeometryOperation]:
        """
        Returns the supported operation class.
        """

        return GeometryOperation

    def _execute(
        self,
        operation: GeometryOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """
        Executes one complete geometry operation.
        """

        operation.validate()
        context.validate()

        result = self._geometry_service.execute(
            operation
        )

        result.validate()

        context.log(
            level="info",
            message=(
                "Geometry operation generated "
                f"solid '{result.output_id}' "
                f"through route '{result.route}'."
            ),
            operation_id=operation.id,
            metadata={
                "route": result.route,
                "output_id": result.output_id,
                "volume": result.solid.volume,
                "tags": operation.tags,
                **result.metadata,
            },
        )

        return OperationExecutorPayload(
            output_id=result.output_id,
            solid=result.solid,
            metadata={
                "executor": (
                    "geometry_operation_executor"
                ),
                "route": result.route,
                "volume": result.solid.volume,
                **result.metadata,
            },
        )

    @property
    def geometry_service(
        self,
    ) -> GeometryExecutionService:
        """
        Returns the geometry execution service.
        """

        return self._geometry_service