"""
DOBO CAD Kernel

Geometry Operation Contract

Describes one complete backend-independent geometry
generation operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kernel.contracts.config.geometry_pipeline_configuration import (
    GeometryPipelineConfiguration,
)

from .base_operation import (
    BaseOperation,
    OperationType,
)


@dataclass(frozen=True, slots=True)
class GeometryOperation(BaseOperation):
    """
    Executes one GeometryPipeline configuration.

    The generated Solid is stored under output_id so
    later BooleanOperation objects can reference it.
    """

    configuration: GeometryPipelineConfiguration = field(
        default=None  # type: ignore[arg-type]
    )

    output_id: str = ""

    tags: tuple[str, ...] = ()

    @property
    def operation_type(self) -> OperationType:
        return OperationType.GEOMETRY

    def validate(self) -> None:
        """
        Validates the geometry operation.
        """

        BaseOperation.validate(self)

        if not isinstance(
            self.configuration,
            GeometryPipelineConfiguration,
        ):
            raise TypeError(
                "GeometryOperation configuration must be "
                "a GeometryPipelineConfiguration."
            )

        self.configuration.validate()

        if not isinstance(
            self.output_id,
            str,
        ) or not self.output_id.strip():
            raise ValueError(
                "GeometryOperation output_id "
                "cannot be empty."
            )

        if not isinstance(
            self.tags,
            tuple,
        ):
            raise TypeError(
                "GeometryOperation tags must be a tuple."
            )

        for tag in self.tags:
            if not isinstance(
                tag,
                str,
            ):
                raise TypeError(
                    "GeometryOperation tags must contain "
                    "strings only."
                )

            if not tag.strip():
                raise ValueError(
                    "GeometryOperation tags "
                    "cannot contain empty values."
                )

    @property
    def provider_name(self) -> str:
        """
        Returns the configured Definition Provider name.
        """

        return self.configuration.provider.name

    @property
    def surface_type(self) -> str:
        """
        Returns the configured surface identifier.
        """

        return (
            self.configuration
            .surface
            .surface
            .type
            .value
        )

    @property
    def offset_distance(self) -> float:
        """
        Returns the configured offset thickness.
        """

        return self.configuration.offset.distance