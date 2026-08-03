"""
DOBO CAD Kernel

Provider Registry

Stores and discovers geometry Provider instances.
"""

from __future__ import annotations

from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest
from kernel.plugins.registry import PluginRegistry

from .provider import Provider


class ProviderRegistry(
    PluginRegistry[Provider],
):
    """
    Registry specialized for geometry Providers.
    """

    def register_provider(
        self,
        provider: Provider,
    ) -> None:
        """
        Validates and registers a Provider using
        its canonical name and aliases.
        """

        if not isinstance(
            provider,
            Provider,
        ):
            raise TypeError("ProviderRegistry only accepts " "Provider instances.")

        provider.validate_plugin()

        self.register(
            name=provider.name,
            plugin=provider,
            aliases=provider.aliases,
        )

    def get_provider(
        self,
        name: str,
    ) -> Provider:
        """
        Returns a registered Provider.
        """

        return self.get(name)

    def execute(
        self,
        name: str,
        request: ProviderRequest,
    ) -> ContourSet:
        """
        Finds a Provider and executes it.
        """

        provider = self.get_provider(name)

        return provider.execute(request)


from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest
