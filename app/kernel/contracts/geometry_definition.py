"""
DOBO CAD Kernel

Geometry Definition Contract

Represents one backend-independent planar geometry
definition composed of one outer contour and zero or
more inner contours.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .contour_definition import ContourDefinition


@dataclass(frozen=True, slots=True)
class GeometryDefinition:
    """
    Immutable planar geometry definition.

    The outer contour represents the filled boundary.
    Inner contours represent holes.
    """

    outer_contour: ContourDefinition

    inner_contours: tuple[
        ContourDefinition,
        ...,
    ] = ()

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    source: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete geometry definition.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "GeometryDefinition id cannot be empty."
            )

        if not isinstance(
            self.outer_contour,
            ContourDefinition,
        ):
            raise TypeError(
                "GeometryDefinition outer_contour "
                "must be ContourDefinition."
            )

        self.outer_contour.validate()

        if not self.outer_contour.closed:
            raise ValueError(
                "GeometryDefinition outer_contour "
                "must be closed."
            )

        if not isinstance(
            self.inner_contours,
            tuple,
        ):
            raise TypeError(
                "GeometryDefinition inner_contours "
                "must be a tuple."
            )

        contour_ids: set[str] = {
            self.outer_contour.id
        }

        for contour in self.inner_contours:
            if not isinstance(
                contour,
                ContourDefinition,
            ):
                raise TypeError(
                    "GeometryDefinition inner_contours "
                    "must contain ContourDefinition objects."
                )

            contour.validate()

            if not contour.closed:
                raise ValueError(
                    "GeometryDefinition inner contours "
                    "must be closed."
                )

            if contour.id in contour_ids:
                raise ValueError(
                    "GeometryDefinition cannot contain "
                    f"duplicate contour id '{contour.id}'."
                )

            contour_ids.add(
                contour.id
            )

        if not isinstance(
            self.source,
            str,
        ):
            raise TypeError(
                "GeometryDefinition source "
                "must be a string."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "GeometryDefinition metadata "
                "must be a dictionary."
            )

    @property
    def contour_count(self) -> int:
        """
        Returns outer plus inner contour count.
        """

        return 1 + len(
            self.inner_contours
        )

    @property
    def hole_count(self) -> int:
        """
        Returns the number of inner contours.
        """

        return len(
            self.inner_contours
        )

    @property
    def point_count(self) -> int:
        """
        Returns the total number of contour points.
        """

        return (
            self.outer_contour.count
            + sum(
                contour.count
                for contour in self.inner_contours
            )
        )

    @property
    def contours(
        self,
    ) -> tuple[
        ContourDefinition,
        ...,
    ]:
        """
        Returns outer followed by inner contours.
        """

        return (
            self.outer_contour,
            *self.inner_contours,
        )

    @property
    def bounds(
        self,
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
    ]:
        """
        Returns the outer-contour bounding box.
        """

        return self.outer_contour.bounds
