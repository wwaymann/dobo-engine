"""
DOBO CAD Kernel

Offset Contour Set Contract

Immutable collection of offset contours.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .offset_contour import OffsetContour
from .projected_contour_set import (
    ProjectedContourSet,
)


@dataclass(frozen=True, slots=True)
class OffsetContourSet:
    """
    Collection produced by OffsetEngine.
    """

    contours: tuple[
        OffsetContour,
        ...,
    ]

    source: ProjectedContourSet

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates all offset contours.
        """

        if not self.contours:
            raise ValueError(
                "OffsetContourSet cannot be empty."
            )

        self.source.validate()

        if len(
            self.contours
        ) != self.source.count:
            raise ValueError(
                "OffsetContourSet contour count must "
                "match its source contour count."
            )

        for contour in self.contours:
            contour.validate()

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "OffsetContourSet metadata "
                "must be a dictionary."
            )

    @property
    def count(self) -> int:
        return len(
            self.contours
        )

    @property
    def point_count(self) -> int:
        return sum(
            contour.count
            for contour in self.contours
        )

    @property
    def is_empty(self) -> bool:
        return self.count == 0