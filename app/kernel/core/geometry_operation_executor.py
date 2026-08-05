"""
DOBO CAD Kernel

Geometry Operation Executor

Executes GeometryOperation objects through
the Kernel v2 GeometryPipeline.
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
from kernel.pipeline.geometry_pipeline import (
    GeometryPipeline,
)


class GeometryOperationExecutor(
    OperationExecutor[GeometryOperation],
):
    """
    Executes GeometryOperation objects.

    Flow:

    GeometryOperation
    -> GeometryPipeline
    -> Solid
    -> OperationExecutorPayload
    """

    def __init__(
        self,
        pipeline: GeometryPipeline,
    ) -> None:
        if not isinstance(
            pipeline,
            GeometryPipeline,
        ):
            raise TypeError(
                "GeometryOperationExecutor requires "
                "a GeometryPipeline."
            )

        self._pipeline = pipeline

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

        configuration = (
            operation.configuration
        )

        configuration.validate()

        result = self._pipeline.execute(
            provider_name=(
                configuration.provider.name
            ),
            provider_parameters=dict(
                configuration.provider.parameters
            ),
            placement=(
                configuration
                .surface
                .placement
            ),
            surface=(
                configuration
                .surface
                .surface
            ),
            offset_distance=(
                configuration.offset.distance
            ),
            symmetric_offset=(
                configuration.offset.symmetric
            ),
            metadata={
                "operation_id": operation.id,
                "operation_name": (
                    operation.display_name
                ),
                "configuration_id": (
                    configuration.id
                ),
                "project_name": (
                    configuration.project_name
                ),
                "units": configuration.units,
                "tags": operation.tags,
                **configuration.metadata,
                **operation.metadata,
            },
        )

        result.validate()

        context.log(
            level="info",
            message=(
                "Geometry operation generated "
                f"solid '{operation.output_id}'."
            ),
            operation_id=operation.id,
            metadata={
                "provider": (
                    operation.provider_name
                ),
                "surface": (
                    operation.surface_type
                ),
                "offset_distance": (
                    operation.offset_distance
                ),
                "definition_points": (
                    result
                    .definitions
                    .point_count
                ),
                "projected_points": (
                    result
                    .projected
                    .point_count
                ),
                "offset_points": (
                    result
                    .offset
                    .point_count
                ),
                "volume": result.solid.volume,
            },
        )

        return OperationExecutorPayload(
            output_id=operation.output_id,
            solid=result.solid,
            metadata={
                "executor": (
                    "geometry_operation_executor"
                ),
                "provider": (
                    operation.provider_name
                ),
                "surface": (
                    operation.surface_type
                ),
                "offset_distance": (
                    operation.offset_distance
                ),
                "definition_count": (
                    result.definitions.count
                ),
                "definition_point_count": (
                    result
                    .definitions
                    .point_count
                ),
                "projected_count": (
                    result.projected.count
                ),
                "projected_point_count": (
                    result
                    .projected
                    .point_count
                ),
                "offset_count": (
                    result.offset.count
                ),
                "offset_point_count": (
                    result
                    .offset
                    .point_count
                ),
                "volume": result.solid.volume,
            },
        )