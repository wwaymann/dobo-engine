"""
DOBO CAD Kernel

Projected Contour Set
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .projected_contour import (
    ProjectedContour,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProjectedContourSet:
    """
    Collection of projected contours.
    """

    contours: tuple[
        ProjectedContour,
        ...,
    ]

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(
        self,
    ) -> None:

        if not self.contours:
            raise ValueError(
                "ProjectedContourSet "
                "cannot be empty."
            )

        for contour in self.contours:
            contour.validate()

    @property
    def count(
        self,
    ) -> int:

        return len(
            self.contours
        )

    @property
    def point_count(
        self,
    ) -> int:

        return sum(
            contour.count
            for contour in self.contours
        )