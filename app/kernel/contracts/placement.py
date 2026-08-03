"""
DOBO CAD Kernel

Placement Contract

Defines where and how geometry must be positioned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Vector3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class Placement:
    """
    Describes the requested position, orientation
    and scale of geometry.

    Placement contains no geometric topology.
    """

    position: Vector3 = (
        0.0,
        0.0,
        0.0,
    )

    rotation: Vector3 = (
        0.0,
        0.0,
        0.0,
    )

    scale: Vector3 = (
        1.0,
        1.0,
        1.0,
    )

    alignment: str = "center"

    anchor: str = "center"

    angle_degrees: float | None = None

    surface_coordinates: tuple[
        float,
        float,
    ] | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates placement parameters.
        """

        if any(
            scale_value <= 0
            for scale_value in self.scale
        ):
            raise ValueError(
                "Placement scale values must "
                "be greater than 0."
            )

        if self.alignment not in {
            "left",
            "center",
            "right",
        }:
            raise ValueError(
                "Placement alignment must be "
                "'left', 'center' or 'right'."
            )

        if self.anchor not in {
            "center",
            "top",
            "bottom",
            "left",
            "right",
        }:
            raise ValueError(
                "Unsupported Placement anchor."
            )