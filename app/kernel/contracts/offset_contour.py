"""
DOBO CAD Kernel

Offset Contour Contract

Represents one projected contour after thickness
has been applied along its local normals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .offset_point import OffsetPoint
from .projected_point import Point3D


@dataclass(frozen=True, slots=True)
class OffsetContour:
    """
    Contains one OffsetPoint per projected point.
    """

    points: tuple[
        OffsetPoint,
        ...,
    ]

    closed: bool = True

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete offset contour.
        """

        minimum_point_count = (
            3
            if self.closed
            else 2
        )

        if len(
            self.points
        ) < minimum_point_count:
            raise ValueError(
                "OffsetContour contains too few points."
            )

        for point in self.points:
            point.validate()

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "OffsetContour metadata "
                "must be a dictionary."
            )

    @property
    def count(self) -> int:
        return len(
            self.points
        )

    @property
    def inner_points(
        self,
    ) -> tuple[
        Point3D,
        ...,
    ]:
        return tuple(
            point.inner_tuple
            for point in self.points
        )

    @property
    def outer_points(
        self,
    ) -> tuple[
        Point3D,
        ...,
    ]:
        return tuple(
            point.outer_tuple
            for point in self.points
        )