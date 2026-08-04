"""
DOBO CAD Kernel

Projected Contour Contract

Represents one contour projected into three-dimensional
space, including an optional local normal per point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .projected_point import (
    Point3D,
    ProjectedPoint,
)


Vector3 = tuple[float, float, float]


@dataclass(
    frozen=True,
    slots=True,
)
class ProjectedContour:
    """
    One contour projected onto a surface.

    The normals collection is optional for planar
    compatibility, but when present it must contain
    exactly one normal per projected point.
    """

    points: tuple[
        ProjectedPoint,
        ...,
    ]

    closed: bool = True

    normals: tuple[
        Vector3,
        ...,
    ] = ()

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(
        self,
    ) -> None:
        """
        Validates projected points and local normals.
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
                "ProjectedContour contains too few points."
            )

        for point in self.points:
            point.validate()

        if self.normals:
            if len(
                self.normals
            ) != len(
                self.points
            ):
                raise ValueError(
                    "ProjectedContour must contain one "
                    "normal per projected point."
                )

            for normal in self.normals:
                self._validate_normal(
                    normal
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "ProjectedContour metadata "
                "must be a dictionary."
            )

    @property
    def count(
        self,
    ) -> int:
        """
        Returns the number of projected points.
        """

        return len(
            self.points
        )

    @property
    def has_normals(
        self,
    ) -> bool:
        """
        Returns whether local point normals exist.
        """

        return bool(
            self.normals
        )

    @property
    def point_tuples(
        self,
    ) -> tuple[
        Point3D,
        ...,
    ]:
        """
        Returns all points as plain tuples.
        """

        return tuple(
            point.tuple
            for point in self.points
        )

    @staticmethod
    def _validate_normal(
        normal: Vector3,
    ) -> None:
        """
        Validates one normalized three-dimensional vector.
        """

        if not isinstance(
            normal,
            tuple,
        ) or len(
            normal
        ) != 3:
            raise ValueError(
                "ProjectedContour normal must contain "
                "three numeric values."
            )

        for coordinate in normal:
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
                    "ProjectedContour normal coordinates "
                    "must be numeric."
                )

        length_squared = (
            float(
                normal[0]
            )
            ** 2
            + float(
                normal[1]
            )
            ** 2
            + float(
                normal[2]
            )
            ** 2
        )

        if length_squared <= 1e-18:
            raise ValueError(
                "ProjectedContour normal cannot "
                "have zero length."
            )