"""
DOBO CAD Kernel

ContourDefinitionSet Contract

Collection of ContourDefinition objects.

This contract is backend-independent and contains
pure mathematical geometry only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contour_definition import ContourDefinition


@dataclass(frozen=True, slots=True)
class ContourDefinitionSet:
    """
    Immutable collection of ContourDefinition objects.
    """

    contours: tuple[ContourDefinition, ...] = ()

    source: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the collection.
        """

        if len(self.contours) == 0:
            raise ValueError(
                "ContourDefinitionSet cannot be empty."
            )

        for contour in self.contours:
            contour.validate()

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "ContourDefinitionSet metadata "
                "must be a dictionary."
            )

    @property
    def count(self) -> int:
        """
        Number of contours.
        """

        return len(
            self.contours
        )

    @property
    def is_empty(self) -> bool:
        """
        Returns True if no contours exist.
        """

        return self.count == 0

    @property
    def point_count(self) -> int:
        """
        Total number of points.
        """

        return sum(
            contour.count
            for contour in self.contours
        )

    @property
    def bounds(
        self,
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
    ]:
        """
        Returns the global bounding box.
        """

        if self.is_empty:
            raise ValueError(
                "Cannot compute bounds "
                "for an empty ContourDefinitionSet."
            )

        minimum_x = float("inf")
        minimum_y = float("inf")
        maximum_x = float("-inf")
        maximum_y = float("-inf")

        for contour in self.contours:
            lower, upper = contour.bounds

            minimum_x = min(
                minimum_x,
                lower[0],
            )

            minimum_y = min(
                minimum_y,
                lower[1],
            )

            maximum_x = max(
                maximum_x,
                upper[0],
            )

            maximum_y = max(
                maximum_y,
                upper[1],
            )

        return (
            (
                minimum_x,
                minimum_y,
            ),
            (
                maximum_x,
                maximum_y,
            ),
        )