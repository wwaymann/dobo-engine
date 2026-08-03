"""
DOBO CAD Kernel

Contour Contract

A Contour represents a single closed two-dimensional loop.

It is the fundamental geometric primitive exchanged between
Providers, Surface Engine and Extrusion Engine.

A Contour is independent from any CAD backend implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Contour:
    """
    Represents a single closed contour.

    A Contour does not contain solid geometry.

    A Contour is immutable from the Kernel perspective.
    """

    id: str = field(default_factory=lambda: str(uuid4()))

    geometry: Any = None
    """
    Backend-specific 2D geometry.

    Examples:

    - CadQuery Wire
    - OCC Wire
    - SVG Path
    - Polyline

    The Kernel does not assume a concrete implementation.
    """

    metadata: dict[str, Any] = field(default_factory=dict)

    source: str = ""
    """
    Name of the Provider that generated this contour.

    Examples:

    circle

    polygon

    svg

    text
    """

    def is_valid(self) -> bool:
        """
        Returns whether the contour contains valid geometry.

        The current implementation only checks that geometry exists.

        Future versions may validate:

        - closed loops
        - self intersections
        - orientation
        - topology
        """

        return self.geometry is not None

    def copy(self) -> "Contour":
        """
        Returns a shallow copy of the contour.
        """

        return Contour(
            geometry=self.geometry,
            metadata=self.metadata.copy(),
            source=self.source,
        )