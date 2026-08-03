"""
DOBO CAD Kernel

Solid Contract

Represents valid three-dimensional geometry generated
by the Extrusion Engine and consumed by the Boolean Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


Vector3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """
    Axis-aligned bounding box of a Solid.
    """

    minimum: Vector3
    maximum: Vector3

    def validate(self) -> None:
        """
        Validates bounding-box dimensions.
        """

        if len(self.minimum) != 3:
            raise ValueError(
                "BoundingBox minimum must contain three values."
            )

        if len(self.maximum) != 3:
            raise ValueError(
                "BoundingBox maximum must contain three values."
            )

        for minimum_value, maximum_value in zip(
            self.minimum,
            self.maximum,
        ):
            if minimum_value > maximum_value:
                raise ValueError(
                    "BoundingBox minimum values cannot exceed "
                    "maximum values."
                )

    @property
    def size(self) -> Vector3:
        """
        Returns bounding-box dimensions.
        """

        return (
            self.maximum[0] - self.minimum[0],
            self.maximum[1] - self.minimum[1],
            self.maximum[2] - self.minimum[2],
        )


@dataclass(frozen=True, slots=True)
class SolidValidation:
    """
    Describes the validation state of a Solid.
    """

    is_valid: bool = False

    is_closed: bool = False

    is_manifold: bool = False

    is_watertight: bool = False

    errors: tuple[str, ...] = ()

    warnings: tuple[str, ...] = ()

    def require_valid(self) -> None:
        """
        Raises an error when the Solid is invalid.
        """

        if not self.is_valid:
            message = (
                "; ".join(self.errors)
                if self.errors
                else "Solid validation failed."
            )

            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class Solid:
    """
    Represents valid three-dimensional geometry.

    The geometry field may contain a backend-specific
    solid object, but the contract itself does not depend
    on CadQuery or another CAD implementation.
    """

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    geometry: Any = None

    volume: float | None = None

    center_of_mass: Vector3 | None = None

    bounding_box: BoundingBox | None = None

    validation: SolidValidation = field(
        default_factory=SolidValidation
    )

    source: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the Solid contract.
        """

        if self.geometry is None:
            raise ValueError(
                "Solid requires geometry."
            )

        if self.volume is not None:
            if self.volume <= 0:
                raise ValueError(
                    "Solid volume must be greater than zero."
                )

        if self.center_of_mass is not None:
            if len(self.center_of_mass) != 3:
                raise ValueError(
                    "Solid center_of_mass must contain "
                    "three values."
                )

        if self.bounding_box is not None:
            self.bounding_box.validate()

        self.validation.require_valid()

    @property
    def is_valid(self) -> bool:
        """
        Returns the Solid validation state.
        """

        return self.validation.is_valid