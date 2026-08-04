"""
DOBO CAD Kernel

Export Configuration Contract

Defines how and where the final ModelState
must be exported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExportFormat(str, Enum):
    """
    Export formats supported by the Kernel.
    """

    STEP = "step"
    STL = "stl"
    THREE_MF = "3mf"


@dataclass(frozen=True, slots=True)
class ExportConfiguration:
    """
    Configuration for the Export stage.
    """

    enabled: bool = False

    format: ExportFormat = ExportFormat.STEP

    destination: str = ""

    tolerance: float = 0.01

    angular_tolerance: float = 0.1

    units: str = "mm"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the Export configuration.
        """

        if not self.enabled:
            return

        if not self.destination.strip():
            raise ValueError(
                "Enabled ExportConfiguration requires "
                "a destination."
            )

        if self.tolerance <= 0:
            raise ValueError(
                "Export tolerance must be greater than zero."
            )

        if self.angular_tolerance <= 0:
            raise ValueError(
                "Export angular_tolerance must be "
                "greater than zero."
            )

        if self.units not in {
            "mm",
            "cm",
            "m",
            "in",
        }:
            raise ValueError(
                "Export units must be "
                "'mm', 'cm', 'm' or 'in'."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "ExportConfiguration metadata "
                "must be a dictionary."
            )