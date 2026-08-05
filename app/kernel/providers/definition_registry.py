"""
DOBO CAD Kernel

Definition Provider Registry

Stores backend-independent geometry providers.
"""

from __future__ import annotations

from kernel.providers.definition_provider import (
    DefinitionProviderInterface,
)
from kernel.contracts.contour_definition_set import (
    ContourDefinitionSet,
)

class DefinitionProviderRegistry:
    """
    Registry for mathematical Definition Providers.
    """

    def __init__(self) -> None:
        self._providers: dict[
            str,
            DefinitionProviderInterface,
        ] = {}

    def register_provider(
        self,
        provider: DefinitionProviderInterface,
    ) -> None:
        """
        Registers a provider and all its aliases.
        """

        provider_name = self._normalize_name(
            provider.name
        )

        if not provider_name:
            raise ValueError(
                "Definition Provider name cannot be empty."
            )

        names = (
            provider_name,
            *(
                self._normalize_name(
                    alias
                )
                for alias in provider.aliases
            ),
        )

        for name in names:
            if not name:
                raise ValueError(
                    "Definition Provider aliases "
                    "cannot be empty."
                )

            existing = self._providers.get(
                name
            )

            if (
                existing is not None
                and existing is not provider
            ):
                raise ValueError(
                    "Definition Provider name "
                    f"'{name}' is already registered."
                )

        for name in names:
            self._providers[
                name
            ] = provider

    def get_provider(
        self,
        name: str,
    ) -> DefinitionProviderInterface:
        """
        Returns a registered provider.
        """

        normalized_name = self._normalize_name(
            name
        )

        provider = self._providers.get(
            normalized_name
        )

        if provider is None:
            available = ", ".join(
                self.names()
            )

            raise KeyError(
                "Unknown Definition Provider "
                f"'{name}'. Available: {available}"
            )

        return provider

    def execute(
        self,
        name: str,
        parameters: dict[str, object],
        metadata: dict[str, object] | None = None,
    ) -> ContourDefinitionSet:
        """
        Executes one registered Definition Provider.
        """

        provider = self.get_provider(
            name
        )

        from kernel.contracts.provider_request import (
            ProviderRequest,
        )

        request = ProviderRequest(
            provider=provider.name,
            parameters=dict(
                parameters
            ),
            metadata=(
                dict(
                    metadata
                )
                if metadata is not None
                else {}
            ),
        )

        result = provider.execute(
            request
        )

        result.validate()

        return result

    def names(self) -> tuple[str, ...]:
        """
        Returns registered canonical provider names.
        """

        canonical_names = {
            provider.name
            for provider in self._providers.values()
        }

        return tuple(
            sorted(
                canonical_names
            )
        )

    @staticmethod
    def _normalize_name(
        value: str,
    ) -> str:
        """
        Normalizes provider identifiers.
        """

        return value.strip().lower()