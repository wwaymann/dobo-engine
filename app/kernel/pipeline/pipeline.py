"""
DOBO CAD Kernel

Kernel Pipeline

Coordinates Provider execution and produces
the first geometry output of the Kernel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest
from kernel.providers.registry import ProviderRegistry


@dataclass(frozen=True, slots=True)
class ProviderPipelineResult:
    """
    Result returned by the initial Provider pipeline.
    """

    request: ProviderRequest
    contours: ContourSet


class KernelPipeline:
    """
    Initial implementation of the DOBO Kernel Pipeline.

    This version coordinates only the Provider stage.

    Future stages will add:

    - Surface Engine
    - Extrusion Engine
    - Boolean Engine
    - Export Engine
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
    ) -> None:
        self._provider_registry = provider_registry

    def execute_provider(
        self,
        request: ProviderRequest,
    ) -> ProviderPipelineResult:
        """
        Executes one ProviderRequest.

        Flow:

        ProviderRequest
        -> ProviderRegistry
        -> Provider
        -> ContourSet
        """

        request.validate()

        contour_set = (
            self._provider_registry.execute(
                name=request.provider,
                request=request,
            )
        )

        return ProviderPipelineResult(
            request=request,
            contours=contour_set,
        )

    def execute(
        self,
        provider_name: str,
        parameters: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ProviderPipelineResult:
        """
        Convenience method that creates and executes
        a ProviderRequest.
        """

        request = ProviderRequest(
            provider=provider_name,
            parameters=parameters.copy(),
            metadata=(
                metadata.copy()
                if metadata is not None
                else {}
            ),
        )

        return self.execute_provider(
            request
        )