"""
DOBO CAD Kernel

Configuration Contract

Represents the complete immutable project configuration
received by the Kernel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Configuration:
    """
    Complete project configuration.

    Configuration contains parameters and instructions,
    but never generated geometry.
    """

    project_name: str = ""

    units: str = "mm"

    providers: tuple[dict[str, Any], ...] = ()

    placements: tuple[dict[str, Any], ...] = ()

    extrusions: tuple[dict[str, Any], ...] = ()

    booleans: tuple[dict[str, Any], ...] = ()

    export: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the global project configuration.
        """

        if self.units not in {
            "mm",
            "cm",
            "m",
            "in",
        }:
            raise ValueError(
                "Configuration units must be "
                "'mm', 'cm', 'm' or 'in'."
            )

        for index, provider in enumerate(
            self.providers
        ):
            if not isinstance(provider, dict):
                raise ValueError(
                    f"providers[{index}] must be an object."
                )

        for index, placement in enumerate(
            self.placements
        ):
            if not isinstance(placement, dict):
                raise ValueError(
                    f"placements[{index}] must be an object."
                )

        for index, extrusion in enumerate(
            self.extrusions
        ):
            if not isinstance(extrusion, dict):
                raise ValueError(
                    f"extrusions[{index}] must be an object."
                )

        for index, boolean in enumerate(
            self.booleans
        ):
            if not isinstance(boolean, dict):
                raise ValueError(
                    f"booleans[{index}] must be an object."
                )