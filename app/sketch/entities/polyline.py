"""
DOBO Sketch

Polyline Entity

Defines an ordered sequence of two-dimensional points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .base import (
    SketchEntity,
    SketchEntityType,
)
from .point import SketchPoint


@dataclass(frozen=True, slots=True)
class PolylineEntity(SketchEntity):
    """
    Ordered polyline that may be open or closed.
    """

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    construction: bool = False

    enabled: bool = True

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    points: tuple[
        SketchPoint,
        ...,
    ] = ()

    closed: bool = True

    @property
    def entity_type(self) -> SketchEntityType:
        return SketchEntityType.POLYLINE

    @property
    def point_count(self) -> int:
        return len(
            self.points
        )

    @property
    def segment_count(self) -> int:
        """
        Returns the number of polyline segments.
        """

        if not self.points:
            return 0

        if self.closed:
            return len(
                self.points
            )

        return max(
            0,
            len(
                self.points
            )
            - 1,
        )

    def validate(self) -> None:
        """
        Validates the complete polyline.
        """

        SketchEntity.validate(
            self
        )

        if not isinstance(
            self.points,
            tuple,
        ):
            raise TypeError(
                "PolylineEntity points "
                "must be a tuple."
            )

        if not isinstance(
            self.closed,
            bool,
        ):
            raise TypeError(
                "PolylineEntity closed "
                "must be boolean."
            )

        minimum_count = (
            3
            if self.closed
            else 2
        )

        if len(
            self.points
        ) < minimum_count:
            raise ValueError(
                "PolylineEntity contains "
                "too few points."
            )

        for point in self.points:
            if not isinstance(
                point,
                SketchPoint,
            ):
                raise TypeError(
                    "PolylineEntity points must "
                    "contain SketchPoint objects."
                )

            point.validate()

        point_values = tuple(
            point.tuple
            for point in self.points
        )

        if len(
            set(
                point_values
            )
        ) < minimum_count:
            raise ValueError(
                "PolylineEntity requires enough "
                "distinct points."
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
                    "PolylineEntity cannot contain "
                    "consecutive coincident points."
                )

        if (
            self.closed
            and self.points[0].distance_to(
                self.points[-1]
            )
            <= 1e-12
        ):
            raise ValueError(
                "Closed PolylineEntity must not "
                "repeat its first point at the end."
            )