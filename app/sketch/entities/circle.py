"""
DOBO Sketch

Circle Entity

Defines one circle using center and radius.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .base import (
    SketchEntity,
    SketchEntityType,
)
from .point import SketchPoint


@dataclass(frozen=True, slots=True)
class CircleEntity(SketchEntity):
    """
    Circular sketch entity.
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

    center: SketchPoint = field(
        default_factory=lambda: SketchPoint(
            0.0,
            0.0,
        )
    )

    radius: float = 1.0

    @property
    def entity_type(self) -> SketchEntityType:
        return SketchEntityType.CIRCLE

    @property
    def point_count(self) -> int:
        return 1

    @property
    def diameter(self) -> float:
        return float(
            self.radius
        ) * 2.0

    @property
    def circumference(self) -> float:
        return (
            2.0
            * math.pi
            * float(
                self.radius
            )
        )

    def validate(self) -> None:
        """
        Validates the complete circle entity.
        """

        SketchEntity.validate(
            self
        )

        if not isinstance(
            self.center,
            SketchPoint,
        ):
            raise TypeError(
                "CircleEntity center must be "
                "a SketchPoint."
            )

        self.center.validate()

        if isinstance(
            self.radius,
            bool,
        ) or not isinstance(
            self.radius,
            (
                int,
                float,
            ),
        ):
            raise TypeError(
                "CircleEntity radius "
                "must be numeric."
            )

        if not math.isfinite(
            float(
                self.radius
            )
        ):
            raise ValueError(
                "CircleEntity radius "
                "must be finite."
            )

        if self.radius <= 0:
            raise ValueError(
                "CircleEntity radius must be "
                "greater than zero."
            )