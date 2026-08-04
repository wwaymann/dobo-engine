"""
DOBO CAD Kernel

Provider Stage

Converts provider configuration into a ContourSet
through the Provider Registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest
from kernel.providers.registry import ProviderRegistry


@dataclass(frozen=True, slots=True)
class ProviderStageResult:
    """
    Immutable result produced by ProviderStage.
    """

    request: ProviderRequest
    contours: ContourSet


class ProviderStage:
    """
    Coordinates the Provider stage of the Kernel.

    Responsibilities:

    - build ProviderRequest;
    - locate the Provider;
    - execute the Provider;
    - return a validated ContourSet.

    It never creates geometry directly.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
    ) -> None:
        self._registry = registry

    def execute(
        self,
        provider_name: str,
        parameters: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ProviderStageResult:
        """
        Executes one configured Provider.
        """

        request = ProviderRequest(
            provider=provider_name,
            parameters=parameters.copy(),
            metadata=(metadata.copy() if metadata is not None else {}),
        )

        request.validate()

        contours = self._registry.execute(
            name=provider_name,
            request=request,
        )

        if contours.is_empty:
            raise RuntimeError("ProviderStage received an empty ContourSet.")

        if not contours.validate():
            raise RuntimeError("ProviderStage received invalid Contours.")

        return ProviderStageResult(
            request=request,
            contours=contours,
        )
