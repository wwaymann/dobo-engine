"""
DOBO CAD Kernel

Offset Point Contract

Represents one projected point together with its
inner and outer offset positions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .projected_point import (
    Point3D,
    ProjectedPoint,
)


Vector3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class OffsetPoint:
    """
    Represents the thickness applied to one
    ProjectedPoint along its local normal.
    """

    source: ProjectedPoint

    normal: Vector3

    inner: ProjectedPoint

    outer: ProjectedPoint

    distance: float

    def validate(self) -> None:
        """
        Validates one offset point.
        """

        self.source.validate()
        self.inner.validate()
        self.outer.validate()

        if self.distance <= 0:
            raise ValueError(
                "OffsetPoint distance must be "
                "greater than zero."
            )

        if not isinstance(
            self.normal,
            tuple,
        ) or len(
            self.normal
        ) != 3:
            raise ValueError(
                "OffsetPoint normal must contain "
                "three values."
            )

        for coordinate in self.normal:
            if isinstance(
                coordinate,
                bool,
            ) or not isinstance(
                coordinate,
                (
                    int,
                    float,
                ),
            ):
                raise TypeError(
                    "OffsetPoint normal coordinates "
                    "must be numeric."
                )

        normal_length_squared = (
            float(
                self.normal[0]
            )
            ** 2
            + float(
                self.normal[1]
            )
            ** 2
            + float(
                self.normal[2]
            )
            ** 2
        )

        if normal_length_squared <= 1e-18:
            raise ValueError(
                "OffsetPoint normal cannot "
                "have zero length."
            )

    @property
    def source_tuple(self) -> Point3D:
        return self.source.tuple

    @property
    def inner_tuple(self) -> Point3D:
        return self.inner.tuple

    @property
    def outer_tuple(self) -> Point3D:
        return self.outer.tuple