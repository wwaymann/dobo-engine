"""
DOBO CAD Kernel

Extrusion Profile Contract

Defines how a SurfacePlacement becomes a Solid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExtrusionMode(str, Enum):
    """
    Supported extrusion modes.
    """

    NORMAL = "normal"

    BIDIRECTIONAL = "bidirectional"

    DIRECTIONAL = "directional"

    SWEEP = "sweep"

    LOFT = "loft"

    REVOLVE = "revolve"


Vector3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ExtrusionProfile:
    """
    Describes the extrusion strategy.

    Contains no geometry.
    """

    mode: ExtrusionMode = ExtrusionMode.NORMAL

    depth: float = 1.0

    direction: Vector3 | None = None

    taper_degrees: float = 0.0

    shell_thickness: float | None = None

    offset: float = 0.0

    merge: bool = True

    tolerance: float = 0.01

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the extrusion profile.
        """

        if self.depth <= 0:
            raise ValueError(
                "Extrusion depth must be greater than zero."
            )

        if self.shell_thickness is not None:
            if self.shell_thickness <= 0:
                raise ValueError(
                    "Shell thickness must be greater than zero."
                )

            if self.shell_thickness >= self.depth:
                raise ValueError(
                    "Shell thickness must be smaller than extrusion depth."
                )

        if self.tolerance <= 0:
            raise ValueError(
                "Tolerance must be greater than zero."
            )

        if self.mode == ExtrusionMode.DIRECTIONAL:

            if self.direction is None:
                raise ValueError(
                    "Directional extrusion requires a direction vector."
                )

            if len(self.direction) != 3:
                raise ValueError(
                    "Direction vector must contain three values."
                )

            if all(
                float(value) == 0.0
                for value in self.direction
            ):
                raise ValueError(
                    "Direction vector cannot be zero."
                )