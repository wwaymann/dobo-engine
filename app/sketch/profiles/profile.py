"""
DOBO Sketch

Profile Contract

Represents one closed, ordered and validated
two-dimensional sketch profile.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sketch.entities import (
    Point2D,
    SketchPoint,
)


Bounds2D = tuple[
    tuple[float, float],
    tuple[float, float],
]


@dataclass(frozen=True, slots=True)
class Profile:
    """
    Immutable closed profile produced by ProfileBuilder.

    A Profile is independent from CadQuery and contains
    only ordered two-dimensional points.
    """

    points: tuple[
        SketchPoint,
        ...,
    ]

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    source_entity_ids: tuple[
        str,
        ...,
    ] = ()

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete profile.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "Profile id cannot be empty."
            )

        if not isinstance(
            self.points,
            tuple,
        ):
            raise TypeError(
                "Profile points must be a tuple."
            )

        if len(
            self.points
        ) < 3:
            raise ValueError(
                "Profile requires at least "
                "three points."
            )

        point_values: list[
            Point2D
        ] = []

        for point in self.points:
            if not isinstance(
                point,
                SketchPoint,
            ):
                raise TypeError(
                    "Profile points must contain "
                    "SketchPoint objects."
                )

            point.validate()

            point_values.append(
                point.tuple
            )

        if len(
            set(
                point_values
            )
        ) < 3:
            raise ValueError(
                "Profile requires at least "
                "three distinct points."
            )

        for current, following in zip(
            self.points,
            self.points[1:],
            strict=False,
        ):
            if (
                current.distance_to(
                    following
                )
                <= 1e-12
            ):
                raise ValueError(
                    "Profile cannot contain "
                    "consecutive coincident points."
                )

        if (
            self.points[0].distance_to(
                self.points[-1]
            )
            <= 1e-12
        ):
            raise ValueError(
                "Profile must not repeat its "
                "first point at the end."
            )

        if not isinstance(
            self.source_entity_ids,
            tuple,
        ):
            raise TypeError(
                "Profile source_entity_ids "
                "must be a tuple."
            )

        for entity_id in self.source_entity_ids:
            if not isinstance(
                entity_id,
                str,
            ) or not entity_id.strip():
                raise ValueError(
                    "Profile source entity IDs "
                    "must be non-empty strings."
                )

        if len(
            set(
                self.source_entity_ids
            )
        ) != len(
            self.source_entity_ids
        ):
            raise ValueError(
                "Profile source_entity_ids "
                "cannot contain duplicates."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "Profile metadata must be "
                "a dictionary."
            )

        if self.area <= 1e-12:
            raise ValueError(
                "Profile area must be "
                "greater than zero."
            )

    @property
    def point_count(self) -> int:
        """
        Returns the number of ordered profile points.
        """

        return len(
            self.points
        )

    @property
    def segment_count(self) -> int:
        """
        Returns the number of closed profile segments.
        """

        return self.point_count

    @property
    def tuples(
        self,
    ) -> tuple[
        Point2D,
        ...,
    ]:
        """
        Returns profile points as plain tuples.
        """

        return tuple(
            point.tuple
            for point in self.points
        )

    @property
    def signed_area(self) -> float:
        """
        Returns the signed polygon area.

        Positive:
            counterclockwise orientation.

        Negative:
            clockwise orientation.
        """

        total = 0.0

        for index, current in enumerate(
            self.points
        ):
            following = self.points[
                (
                    index + 1
                )
                % self.point_count
            ]

            total += (
                current.x
                * following.y
                - following.x
                * current.y
            )

        return total / 2.0

    @property
    def area(self) -> float:
        """
        Returns the absolute polygon area.
        """

        return abs(
            self.signed_area
        )

    @property
    def clockwise(self) -> bool:
        """
        Returns whether the profile orientation
        is clockwise.
        """

        return self.signed_area < 0.0

    @property
    def counterclockwise(self) -> bool:
        """
        Returns whether the profile orientation
        is counterclockwise.
        """

        return self.signed_area > 0.0

    @property
    def perimeter(self) -> float:
        """
        Returns the closed profile perimeter.
        """

        total = 0.0

        for index, current in enumerate(
            self.points
        ):
            following = self.points[
                (
                    index + 1
                )
                % self.point_count
            ]

            total += current.distance_to(
                following
            )

        return total

    @property
    def bounds(self) -> Bounds2D:
        """
        Returns the profile bounding box.
        """

        all_x = tuple(
            point.x
            for point in self.points
        )

        all_y = tuple(
            point.y
            for point in self.points
        )

        return (
            (
                min(
                    all_x
                ),
                min(
                    all_y
                ),
            ),
            (
                max(
                    all_x
                ),
                max(
                    all_y
                ),
            ),
        )

    @property
    def centroid(self) -> Point2D:
        """
        Returns the polygon centroid.

        Uses the area-weighted polygon centroid formula.
        """

        signed_area = self.signed_area

        if math.isclose(
            signed_area,
            0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "Cannot calculate centroid "
                "for a zero-area Profile."
            )

        accumulated_x = 0.0
        accumulated_y = 0.0

        for index, current in enumerate(
            self.points
        ):
            following = self.points[
                (
                    index + 1
                )
                % self.point_count
            ]

            cross = (
                current.x
                * following.y
                - following.x
                * current.y
            )

            accumulated_x += (
                current.x
                + following.x
            ) * cross

            accumulated_y += (
                current.y
                + following.y
            ) * cross

        scale = (
            1.0
            / (
                6.0
                * signed_area
            )
        )

        return (
            accumulated_x
            * scale,
            accumulated_y
            * scale,
        )

    def contains_point(
        self,
        point: SketchPoint,
    ) -> bool:
        """
        Returns whether a point lies inside the profile.

        Uses the ray-casting algorithm.
        Boundary handling is approximate.
        """

        if not isinstance(
            point,
            SketchPoint,
        ):
            raise TypeError(
                "Profile.contains_point requires "
                "a SketchPoint."
            )

        point.validate()

        inside = False

        for index, current in enumerate(
            self.points
        ):
            following = self.points[
                (
                    index + 1
                )
                % self.point_count
            ]

            intersects = (
                (
                    current.y > point.y
                )
                != (
                    following.y > point.y
                )
            )

            if not intersects:
                continue

            denominator = (
                following.y
                - current.y
            )

            if math.isclose(
                denominator,
                0.0,
                abs_tol=1e-15,
            ):
                continue

            intersection_x = (
                current.x
                + (
                    point.y
                    - current.y
                )
                * (
                    following.x
                    - current.x
                )
                / denominator
            )

            if point.x < intersection_x:
                inside = not inside

        return inside

    def reversed(
        self,
    ) -> "Profile":
        """
        Returns a new Profile with reversed orientation.
        """

        result = Profile(
            points=tuple(
                reversed(
                    self.points
                )
            ),
            id=self.id,
            source_entity_ids=(
                self.source_entity_ids
            ),
            metadata={
                **self.metadata,
                "reversed": True,
            },
        )

        result.validate()

        return result