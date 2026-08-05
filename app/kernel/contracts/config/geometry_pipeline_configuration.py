"""
DOBO CAD Kernel

Geometry Pipeline Configuration Contract

Represents one complete Kernel v2 geometry operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from kernel.contracts.config.offset_configuration import (
    OffsetConfiguration,
)
from kernel.contracts.config.provider_configuration import (
    ProviderConfiguration,
)
from kernel.contracts.config.surface_configuration import (
    SurfaceConfiguration,
)


@dataclass(frozen=True, slots=True)
class GeometryPipelineConfiguration:
    """
    Complete configuration consumed by GeometryPipeline.

    Flow:

    ProviderConfiguration
    -> SurfaceConfiguration
    -> OffsetConfiguration
    -> Solid
    """

    provider: ProviderConfiguration

    surface: SurfaceConfiguration

    offset: OffsetConfiguration

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    project_name: str = ""

    units: str = "mm"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete geometry configuration.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "GeometryPipelineConfiguration id "
                "cannot be empty."
            )

        if not isinstance(
            self.project_name,
            str,
        ):
            raise TypeError(
                "GeometryPipelineConfiguration "
                "project_name must be a string."
            )

        if self.units not in {
            "mm",
            "cm",
            "m",
            "in",
        }:
            raise ValueError(
                "GeometryPipelineConfiguration units "
                "must be 'mm', 'cm', 'm' or 'in'."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "GeometryPipelineConfiguration metadata "
                "must be a dictionary."
            )

        self.provider.validate()
        self.surface.validate()
        self.offset.validate()