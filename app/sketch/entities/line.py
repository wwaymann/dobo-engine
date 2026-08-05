"""
DOBO Sketch

Line Entity

Defines one straight segment between two points.
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
class LineEntity(SketchEntity):
    """
    Straight sketch segment.
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

    start: SketchPoint = field(
        default_factory=lambda: SketchPoint(
            0.0,
            0.0,
        )
    )

    end: SketchPoint = field(
        default_factory=lambda: SketchPoint(
            1.0,
            0.0,
        )
    )

    @property
    def entity_type(self) -> SketchEntityType:
        return SketchEntityType.LINE

    @property
    def point_count(self) -> int:
        return 2

    @property
    def length(self) -> float:
        """
        Returns line length.
        """

        return self.start.distance_to(
            self.end
        )

    def validate(self) -> None:
        """
        Validates the complete line entity.
        """

        SketchEntity.validate(
            self
        )

        if not isinstance(
            self.start,
            SketchPoint,
        ):
            raise TypeError(
                "LineEntity start must be "
                "a SketchPoint."
            )

        if not isinstance(
            self.end,
            SketchPoint,
        ):
            raise TypeError(
                "LineEntity end must be "
                "a SketchPoint."
            )

        self.start.validate()
        self.end.validate()

        if self.length <= 1e-12:
            raise ValueError(
                "LineEntity start and end "
                "cannot be coincident."
            )