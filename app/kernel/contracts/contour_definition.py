"""
DOBO CAD Kernel

ContourDefinition Contract

Represents one backend-independent two-dimensional
closed or open contour.

This contract contains mathematical geometry only.
It must never contain CadQuery, OpenCascade or another
CAD-backend object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


Point2D = tuple[float, float]


@dataclass(frozen=True, slots=True)
class ContourDefinition:
    """
    Represents one ordered two-dimensional contour.

    The Provider is responsible for generating these
    points in local coordinates.

    A closed contour requires at least three distinct
    points.

    An open contour requires at least two distinct
    points.
    """

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    points: tuple[Point2D, ...] = ()

    closed: bool = True

    source: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the contour definition.
        """

        minimum_point_count = (
            3
            if self.closed
            else 2
        )

        if len(self.points) < minimum_point_count:
            raise ValueError(
                "Closed ContourDefinition requires at least "
                "three points."
                if self.closed
                else
                "Open ContourDefinition requires at least "
                "two points."
            )

        for index, point in enumerate(
            self.points
        ):
            if not isinstance(
                point,
                tuple,
            ):
                raise TypeError(
                    f"ContourDefinition points[{index}] "
                    "must be a tuple."
                )

            if len(point) != 2:
                raise ValueError(
                    f"ContourDefinition points[{index}] "
                    "must contain two values."
                )

            for coordinate in point:
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
                        "ContourDefinition coordinates "
                        "must be numeric."
                    )

        distinct_points = {
            (
                float(point[0]),
                float(point[1]),
            )
            for point in self.points
        }

        if len(
            distinct_points
        ) < minimum_point_count:
            raise ValueError(
                "ContourDefinition does not contain "
                "enough distinct points."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "ContourDefinition metadata "
                "must be a dictionary."
            )

    @property
    def count(self) -> int:
        """
        Returns the number of contour points.
        """

        return len(
            self.points
        )

    @property
    def is_empty(self) -> bool:
        """
        Returns True when no points exist.
        """

        return len(
            self.points
        ) == 0

    @property
    def bounds(
        self,
    ) -> tuple[
        Point2D,
        Point2D,
    ]:
        """
        Returns the two-dimensional bounding box.

        Result:

        (
            (minimum_x, minimum_y),
            (maximum_x, maximum_y),
        )
        """

        if self.is_empty:
            raise ValueError(
                "Cannot calculate bounds "
                "for an empty ContourDefinition."
            )

        minimum_x = min(
            point[0]
            for point in self.points
        )

        minimum_y = min(
            point[1]
            for point in self.points
        )

        maximum_x = max(
            point[0]
            for point in self.points
        )

        maximum_y = max(
            point[1]
            for point in self.points
        )

        return (
            (
                float(minimum_x),
                float(minimum_y),
            ),
            (
                float(maximum_x),
                float(maximum_y),
            ),
        )