"""
DOBO CAD Kernel

Offset Configuration Contract

Defines how projected geometry receives thickness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OffsetConfiguration:
    """
    Configuration for the mathematical OffsetEngine.

    symmetric=True:
        Half the distance is applied inward and half
        outward.

    symmetric=False:
        The projected contour remains the inner layer
        and the complete distance is applied outward.
    """

    distance: float

    symmetric: bool = True

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the offset configuration.
        """

        if isinstance(
            self.distance,
            bool,
        ) or not isinstance(
            self.distance,
            (
                int,
                float,
            ),
        ):
            raise TypeError(
                "OffsetConfiguration distance "
                "must be numeric."
            )

        if self.distance <= 0:
            raise ValueError(
                "OffsetConfiguration distance "
                "must be greater than zero."
            )

        if not isinstance(
            self.symmetric,
            bool,
        ):
            raise TypeError(
                "OffsetConfiguration symmetric "
                "must be boolean."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "OffsetConfiguration metadata "
                "must be a dictionary."
            )