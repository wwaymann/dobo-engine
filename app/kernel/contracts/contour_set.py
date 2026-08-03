"""
DOBO CAD Kernel

ContourSet Contract

Represents a collection of Contours belonging to the same
geometric entity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .contour import Contour


@dataclass(slots=True)
class ContourSet:
    """
    A collection of related contours.

    Examples

    - Circle
    - Letter
    - Word
    - SVG
    - Logo
    """

    id: str = field(default_factory=lambda: str(uuid4()))

    contours: list[Contour] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    source: str = ""

    def add(self, contour: Contour) -> None:
        """Adds a contour to the collection."""

        self.contours.append(contour)

    def extend(
        self,
        contours: list[Contour],
    ) -> None:
        """Adds multiple contours."""

        self.contours.extend(contours)

    @property
    def count(self) -> int:
        """Number of contours."""

        return len(self.contours)

    @property
    def is_empty(self) -> bool:
        """Returns True when no contours exist."""

        return len(self.contours) == 0

    def validate(self) -> bool:
        """Returns True if every contour is valid."""

        return all(
            contour.is_valid()
            for contour in self.contours
        )