"""
DOBO CAD Kernel

Geometry Operation Contract

Describes one backend-independent geometry generation
operation.

Supports the legacy GeometryPipelineConfiguration path
and the new GeometryRequest intermediate representation
during the controlled Kernel migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kernel.contracts.config.geometry_pipeline_configuration import (
    GeometryPipelineConfiguration,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
)

from .base_operation import (
    BaseOperation,
    OperationType,
)


@dataclass(frozen=True, slots=True)
class GeometryOperation(BaseOperation):
    """
    Executes one geometry generation request.

    Exactly one input must be supplied:

    - configuration:
        Legacy provider/projection/offset pipeline.

    - request:
        Universal GeometryRequest route.
    """

    configuration: (
        GeometryPipelineConfiguration
        | None
    ) = None

    request: GeometryRequest | None = None

    output_id: str = ""

    tags: tuple[str, ...] = ()

    @property
    def operation_type(self) -> OperationType:
        return OperationType.GEOMETRY

    def validate(self) -> None:
        """
        Validates the complete geometry operation.
        """

        BaseOperation.validate(
            self
        )

        has_configuration = (
            self.configuration is not None
        )

        has_request = (
            self.request is not None
        )

        if has_configuration == has_request:
            raise ValueError(
                "GeometryOperation requires exactly "
                "one of configuration or request."
            )

        if self.configuration is not None:
            if not isinstance(
                self.configuration,
                GeometryPipelineConfiguration,
            ):
                raise TypeError(
                    "GeometryOperation configuration "
                    "must be a "
                    "GeometryPipelineConfiguration."
                )

            self.configuration.validate()

        if self.request is not None:
            if not isinstance(
                self.request,
                GeometryRequest,
            ):
                raise TypeError(
                    "GeometryOperation request must be "
                    "a GeometryRequest."
                )

            self.request.validate()

            if (
                self.output_id
                and self.output_id
                != self.request.output_id
            ):
                raise ValueError(
                    "GeometryOperation output_id must "
                    "match GeometryRequest output_id."
                )

        if not isinstance(
            self.output_id,
            str,
        ):
            raise TypeError(
                "GeometryOperation output_id "
                "must be a string."
            )

        if (
            self.request is None
            and not self.output_id.strip()
        ):
            raise ValueError(
                "Legacy GeometryOperation output_id "
                "cannot be empty."
            )

        if not isinstance(
            self.tags,
            tuple,
        ):
            raise TypeError(
                "GeometryOperation tags must be "
                "a tuple."
            )

        for tag in self.tags:
            if not isinstance(
                tag,
                str,
            ):
                raise TypeError(
                    "GeometryOperation tags must "
                    "contain strings only."
                )

            if not tag.strip():
                raise ValueError(
                    "GeometryOperation tags cannot "
                    "contain empty values."
                )

    @property
    def resolved_output_id(self) -> str:
        """
        Returns the effective output identifier.
        """

        if self.request is not None:
            return self.request.output_id

        return self.output_id

    @property
    def uses_configuration(self) -> bool:
        return self.configuration is not None

    @property
    def uses_request(self) -> bool:
        return self.request is not None

    @property
    def provider_name(self) -> str | None:
        """
        Returns the legacy provider name.
        """

        if self.configuration is None:
            return None

        return self.configuration.provider.name

    @property
    def surface_type(self) -> str | None:
        """
        Returns the legacy surface identifier.
        """

        if self.configuration is None:
            return None

        return (
            self.configuration
            .surface
            .surface
            .type
            .value
        )

    @property
    def offset_distance(self) -> float | None:
        """
        Returns the legacy offset distance.
        """

        if self.configuration is None:
            return None

        return self.configuration.offset.distance

    @property
    def geometry_request_type(self) -> str | None:
        """
        Returns the new GeometryRequest operation type.
        """

        if self.request is None:
            return None

        return self.request.operation.value