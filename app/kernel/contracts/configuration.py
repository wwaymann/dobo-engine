"""
DOBO CAD Kernel

Configuration Contract

Represents the complete immutable project configuration
received by KernelPipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from kernel.contracts.config.boolean_configuration import (
    BooleanConfiguration,
)
from kernel.contracts.config.export_configuration import (
    ExportConfiguration,
)
from kernel.contracts.config.extrusion_configuration import (
    ExtrusionConfiguration,
)
from kernel.contracts.config.provider_configuration import (
    ProviderConfiguration,
)
from kernel.contracts.config.surface_configuration import (
    SurfaceConfiguration,
)


@dataclass(frozen=True, slots=True)
class Configuration:
    """
    Complete configuration for one Kernel operation.

    It describes:

    - which Provider generates the geometry;
    - where the geometry is placed;
    - how it is extruded;
    - how it affects ModelState;
    - whether the result must be exported.
    """

    provider: ProviderConfiguration

    surface: SurfaceConfiguration

    extrusion: ExtrusionConfiguration

    boolean: BooleanConfiguration

    export: ExportConfiguration = field(
        default_factory=ExportConfiguration
    )

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    project_name: str = ""

    units: str = "mm"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete Kernel configuration.
        """

        if self.units not in {
            "mm",
            "cm",
            "m",
            "in",
        }:
            raise ValueError(
                "Configuration units must be "
                "'mm', 'cm', 'm' or 'in'."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "Configuration metadata "
                "must be a dictionary."
            )

        self.provider.validate()
        self.surface.validate()
        self.extrusion.validate()
        self.boolean.validate()
        self.export.validate()