"""
DOBO CAD Kernel

Provider Interface

Defines the public contract implemented by every
geometry Provider.
"""

from __future__ import annotations

from abc import abstractmethod

from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest
from kernel.plugins.plugin import Plugin


class Provider(Plugin):
    """
    Base interface for every geometry Provider.

    Providers generate two-dimensional geometry only.
    They never create solids, perform placement,
    execute boolean operations or modify ModelState.
    """

    @abstractmethod
    def validate(
        self,
        request: ProviderRequest,
    ) -> None:
        """
        Validates provider-specific parameters.

        Raises:
            ValueError:
                When the request is invalid.
        """

    @abstractmethod
    def build_contours(
        self,
        request: ProviderRequest,
    ) -> ContourSet:
        """
        Generates a ContourSet from the request.
        """

    def execute(
        self,
        request: ProviderRequest,
    ) -> ContourSet:
        """
        Executes the standard Provider lifecycle:

        1. Validate plugin metadata.
        2. Validate the generic request.
        3. Confirm the requested provider.
        4. Validate provider-specific parameters.
        5. Build and validate the ContourSet.
        """

        self.validate_plugin()
        request.validate()

        valid_names = {
            self.name.strip().lower(),
            *(
                alias.strip().lower()
                for alias in self.aliases
            ),
        }

        requested_name = (
            request.provider
            .strip()
            .lower()
        )

        if requested_name not in valid_names:
            raise ValueError(
                "ProviderRequest targets "
                f"'{request.provider}', but this Provider "
                f"supports {sorted(valid_names)}."
            )

        self.validate(
            request
        )

        contour_set = self.build_contours(
            request
        )

        if not isinstance(
            contour_set,
            ContourSet,
        ):
            raise TypeError(
                f"Provider '{self.name}' must return "
                "a ContourSet."
            )

        if contour_set.is_empty:
            raise ValueError(
                f"Provider '{self.name}' generated "
                "an empty ContourSet."
            )

        if not contour_set.validate():
            raise ValueError(
                f"Provider '{self.name}' generated "
                "invalid Contours."
            )

        return contour_set