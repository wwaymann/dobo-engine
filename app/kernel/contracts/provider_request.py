"""
DOBO CAD Kernel

ProviderRequest Contract

Represents the immutable input sent to a Geometry Provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """
    Request used to invoke a Geometry Provider.

    It contains parameters only and never stores geometry.
    """

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    provider: str = ""

    parameters: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the ProviderRequest.
        """

        if not self.provider.strip():
            raise ValueError(
                "ProviderRequest provider cannot be empty."
            )

        if not isinstance(
            self.parameters,
            dict,
        ):
            raise ValueError(
                "ProviderRequest parameters must be an object."
            )

    def get_parameter(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        """
        Returns a provider parameter.
        """

        return self.parameters.get(
            name,
            default,
        )