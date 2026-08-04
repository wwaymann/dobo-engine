"""
DOBO CAD Kernel

Provider Configuration Contract

Defines which Provider must execute and the parameters
supplied to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderConfiguration:
    """
    Configuration for one Provider execution.
    """

    name: str

    parameters: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the Provider configuration.
        """

        if not self.name.strip():
            raise ValueError(
                "ProviderConfiguration name cannot be empty."
            )

        if not isinstance(
            self.parameters,
            dict,
        ):
            raise TypeError(
                "ProviderConfiguration parameters "
                "must be a dictionary."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "ProviderConfiguration metadata "
                "must be a dictionary."
            )