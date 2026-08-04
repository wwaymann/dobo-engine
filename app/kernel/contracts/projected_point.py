"""
DOBO CAD Kernel

Projected Point Contract
"""

from __future__ import annotations

from dataclasses import dataclass


Point3D = tuple[
    float,
    float,
    float,
]


@dataclass(
    frozen=True,
    slots=True,
)
class ProjectedPoint:
    """
    Represents one point after projection
    onto a surface.
    """

    x: float

    y: float

    z: float

    @property
    def tuple(
        self,
    ) -> Point3D:
        return (
            self.x,
            self.y,
            self.z,
        )

    def validate(
        self,
    ) -> None:

        for value in (
            self.x,
            self.y,
            self.z,
        ):
            if not isinstance(
                value,
                (
                    int,
                    float,
                ),
            ):
                raise TypeError(
                    "ProjectedPoint coordinates "
                    "must be numeric."
                )