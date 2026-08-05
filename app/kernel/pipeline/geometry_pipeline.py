"""
DOBO CAD Kernel

Geometry Pipeline

Coordinates the backend-independent geometry flow:

DefinitionProvider
→ GeometryProjectionEngine
→ OffsetEngine
→ OffsetSolidBuilder
→ Solid
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kernel.contracts.contour_definition_set import (
    ContourDefinitionSet,
)
from kernel.contracts.offset_contour_set import (
    OffsetContourSet,
)
from kernel.contracts.placement import Placement
from kernel.contracts.projected_contour_set import (
    ProjectedContourSet,
)
from kernel.contracts.solid import Solid
from kernel.contracts.surface import Surface
from kernel.providers.definition_registry import (
    DefinitionProviderRegistry,
)
from kernel.services.geometry_projection_engine import (
    GeometryProjectionEngineInterface,
)
from kernel.services.offset_engine import (
    OffsetEngineInterface,
)
from kernel.services.offset_solid_builder import (
    OffsetSolidBuilderInterface,
)


@dataclass(frozen=True, slots=True)
class GeometryPipelineResult:
    """
    Result of one complete GeometryPipeline execution.
    """

    definitions: ContourDefinitionSet

    projected: ProjectedContourSet

    offset: OffsetContourSet

    solid: Solid

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates every pipeline result contract.
        """

        self.definitions.validate()
        self.projected.validate()
        self.offset.validate()
        self.solid.validate()

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "GeometryPipelineResult metadata "
                "must be a dictionary."
            )


class GeometryPipeline:
    """
    Public orchestration service for Kernel v2 geometry.

    The Pipeline performs no geometry algorithms itself.
    """

    def __init__(
        self,
        provider_registry: DefinitionProviderRegistry,
        projection_engine: GeometryProjectionEngineInterface,
        offset_engine: OffsetEngineInterface,
        solid_builder: OffsetSolidBuilderInterface,
    ) -> None:
        self._provider_registry = (
            provider_registry
        )

        self._projection_engine = (
            projection_engine
        )

        self._offset_engine = (
            offset_engine
        )

        self._solid_builder = (
            solid_builder
        )

    def execute(
        self,
        provider_name: str,
        provider_parameters: dict[str, object],
        placement: Placement,
        surface: Surface,
        offset_distance: float,
        symmetric_offset: bool = True,
        metadata: dict[str, object] | None = None,
    ) -> GeometryPipelineResult:
        """
        Executes the complete Kernel v2 geometry flow.
        """

        definitions = (
            self._provider_registry.execute(
                name=provider_name,
                parameters=provider_parameters,
                metadata=metadata,
            )
        )

        projected = (
            self._projection_engine.project(
                contours=definitions,
                placement=placement,
                surface=surface,
            )
        )

        offset_result = (
            self._offset_engine.offset(
                contours=projected,
                distance=offset_distance,
                symmetric=symmetric_offset,
            )
        )

        build_result = (
            self._solid_builder.build(
                offset_result
            )
        )

        result = GeometryPipelineResult(
            definitions=definitions,
            projected=projected,
            offset=offset_result,
            solid=build_result.solid,
            metadata={
                "provider": provider_name,
                "surface": surface.type.value,
                "offset_distance": (
                    offset_distance
                ),
                "symmetric_offset": (
                    symmetric_offset
                ),
                **(
                    metadata
                    if metadata is not None
                    else {}
                ),
            },
        )

        result.validate()

        return result