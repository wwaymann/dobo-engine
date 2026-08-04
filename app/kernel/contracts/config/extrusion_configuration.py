"""
DOBO CAD Kernel

Extrusion Configuration Contract

Defines how a SurfacePlacement becomes a Solid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kernel.contracts.extrusion_profile import (
    ExtrusionProfile,
)


@dataclass(frozen=True, slots=True)
class ExtrusionConfiguration:
    """
    Configuration for the Extrusion stage.
    """

    profile: ExtrusionProfile = field(
        default_factory=ExtrusionProfile
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the Extrusion configuration.
        """

        self.profile.validate()

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "ExtrusionConfiguration metadata "
                "must be a dictionary."
            )