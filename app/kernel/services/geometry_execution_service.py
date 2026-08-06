"""
DOBO CAD Kernel

Geometry Execution Service

Executes GeometryOperation objects through either:

- the legacy GeometryPipelineConfiguration route;
- the extensible GeometryRequest executor registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kernel.contracts.config.geometry_pipeline_configuration import (
    GeometryPipelineConfiguration,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
)
from kernel.contracts.operations import (
    GeometryOperation,
)
from kernel.contracts.solid import (
    Solid,
)
from kernel.geometry import (
    GeometryRequestExecutorRegistry,
)
from kernel.pipeline.geometry_pipeline import (
    GeometryPipeline,
)


@dataclass(frozen=True, slots=True)
class GeometryExecutionResult:
    """
    Result produced by GeometryExecutionService.
    """

    solid: Solid

    output_id: str

    route: str

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete execution result.
        """

        if not isinstance(
            self.solid,
            Solid,
        ):
            raise TypeError(
                "GeometryExecutionResult solid "
                "must be Solid."
            )

        self.solid.validate()

        if not isinstance(
            self.output_id,
            str,
        ) or not self.output_id.strip():
            raise ValueError(
                "GeometryExecutionResult output_id "
                "cannot be empty."
            )

        if self.route not in (
            "configuration",
            "request",
        ):
            raise ValueError(
                "GeometryExecutionResult route must be "
                "'configuration' or 'request'."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "GeometryExecutionResult metadata "
                "must be a dictionary."
            )


class GeometryExecutionService:
    """
    Executes geometry operations independently from the
    Kernel operation framework.

    During migration, both the legacy pipeline and the
    new GeometryRequest registry remain supported.
    """

    def __init__(
        self,
        *,
        pipeline: GeometryPipeline,
        request_registry: GeometryRequestExecutorRegistry,
    ) -> None:
        if not isinstance(
            pipeline,
            GeometryPipeline,
        ):
            raise TypeError(
                "GeometryExecutionService requires "
                "a GeometryPipeline."
            )

        if not isinstance(
            request_registry,
            GeometryRequestExecutorRegistry,
        ):
            raise TypeError(
                "GeometryExecutionService requires "
                "GeometryRequestExecutorRegistry."
            )

        request_registry.validate()

        self._pipeline = pipeline
        self._request_registry = request_registry

    def execute(
        self,
        operation: GeometryOperation,
    ) -> GeometryExecutionResult:
        """
        Executes one GeometryOperation.
        """

        if not isinstance(
            operation,
            GeometryOperation,
        ):
            raise TypeError(
                "GeometryExecutionService requires "
                "GeometryOperation."
            )

        operation.validate()

        if operation.uses_request:
            return self._execute_request(
                operation
            )

        if operation.uses_configuration:
            return self._execute_configuration(
                operation
            )

        raise RuntimeError(
            "GeometryOperation has no executable input."
        )

    def _execute_request(
        self,
        operation: GeometryOperation,
    ) -> GeometryExecutionResult:
        """
        Executes the new GeometryRequest route.
        """

        request = operation.request

        if not isinstance(
            request,
            GeometryRequest,
        ):
            raise TypeError(
                "GeometryOperation request route "
                "requires GeometryRequest."
            )

        result = self._request_registry.execute(
            request
        )

        result.validate()

        execution_result = GeometryExecutionResult(
            solid=result.solid,
            output_id=operation.resolved_output_id,
            route="request",
            metadata={
                "request_id": request.id,
                "request_operation": (
                    request.operation.value
                ),
                "geometry_count": (
                    request.geometry.count
                ),
                "contour_count": (
                    request.geometry.contour_count
                ),
                "point_count": (
                    request.geometry.point_count
                ),
                "generated_geometry_count": (
                    result.geometry_count
                ),
                "volume": result.solid.volume,
                **result.metadata,
            },
        )

        execution_result.validate()

        return execution_result

    def _execute_configuration(
        self,
        operation: GeometryOperation,
    ) -> GeometryExecutionResult:
        """
        Executes the legacy pipeline route.
        """

        configuration = operation.configuration

        if not isinstance(
            configuration,
            GeometryPipelineConfiguration,
        ):
            raise TypeError(
                "GeometryOperation configuration route "
                "requires "
                "GeometryPipelineConfiguration."
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

        execution_result = GeometryExecutionResult(
            solid=result.solid,
            output_id=operation.resolved_output_id,
            route="configuration",
            metadata={
                "configuration_id": (
                    configuration.id
                ),
                "provider": (
                    configuration.provider.name
                ),
                "surface": (
                    configuration
                    .surface
                    .surface
                    .type
                    .value
                ),
                "offset_distance": (
                    configuration.offset.distance
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

        execution_result.validate()

        return execution_result

    @property
    def request_registry(
        self,
    ) -> GeometryRequestExecutorRegistry:
        """
        Returns the GeometryRequest registry.
        """

        return self._request_registry