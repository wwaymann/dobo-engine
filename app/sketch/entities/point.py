"""
DOBO Sketch

Sketch Point

Defines one backend-independent two-dimensional point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


Point2D = tuple[float, float]


@dataclass(frozen=True, slots=True)
class SketchPoint:
    """
    Immutable point in sketch-local coordinates.
    """

    x: float

    y: float

    def validate(self) -> None:
        """
        Validates the point coordinates.
        """

        for name, value in (
            ("x", self.x),
            ("y", self.y),
        ):
            if isinstance(
                value,
                bool,
            ) or not isinstance(
                value,
                (
                    int,
                    float,
                ),
            ):
                raise TypeError(
                    f"SketchPoint {name} "
                    "must be numeric."
                )

            if not math.isfinite(
                float(value)
            ):
                raise ValueError(
                    f"SketchPoint {name} "
                    "must be finite."
                )

    @property
    def tuple(self) -> Point2D:
        """
        Returns the point as a plain tuple.
        """

        return (
            float(self.x),
            float(self.y),
        )

    def distance_to(
        self,
        other: "SketchPoint",
    ) -> float:
        """
        Returns Euclidean distance to another point.
        """

        if not isinstance(
            other,
            SketchPoint,
        ):
            raise TypeError(
                "SketchPoint.distance_to requires "
                "another SketchPoint."
            )

        return math.hypot(
            other.x - self.x,
            other.y - self.y,
        )