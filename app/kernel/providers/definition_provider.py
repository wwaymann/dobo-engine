"""
DOBO CAD Kernel

Definition Provider Interface

Defines the common contract implemented by providers
that generate backend-independent geometry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from kernel.contracts.contour_definition_set import (
    ContourDefinitionSet,
)
from kernel.contracts.provider_request import ProviderRequest


class DefinitionProviderInterface(ABC):
    """
    Public interface for mathematical geometry providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider identifier.
        """

    @property
    def aliases(self) -> tuple[str, ...]:
        """
        Optional alternative identifiers.
        """

        return ()

    @property
    def version(self) -> str:
        """
        Provider implementation version.
        """

        return "1.0.0"

    @property
    def description(self) -> str:
        """
        Human-readable provider description.
        """

        return ""

    @abstractmethod
    def validate(
        self,
        request: ProviderRequest,
    ) -> None:
        """
        Validates a provider request.
        """

    @abstractmethod
    def execute(
        self,
        request: ProviderRequest,
    ) -> ContourDefinitionSet:
        """
        Generates backend-independent 2D geometry.
        """