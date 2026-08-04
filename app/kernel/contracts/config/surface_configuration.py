"""
DOBO CAD Kernel

Surface Configuration Contract

Defines the target Surface and requested Placement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kernel.contracts.placement import Placement
from kernel.contracts.surface import Surface


@dataclass(frozen=True, slots=True)
class SurfaceConfiguration:
    """
    Configuration for the Surface stage.
    """

    surface: Surface

    placement: Placement = field(
        default_factory=Placement
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the Surface configuration.
        """

        self.surface.validate()
        self.placement.validate()

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "SurfaceConfiguration metadata "
                "must be a dictionary."
            )