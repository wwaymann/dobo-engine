"""
DOBO CAD Kernel

Extrusion Stage

Coordinates the Extrusion Engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernel.contracts.extrusion_profile import (
    ExtrusionProfile,
)
from kernel.contracts.solid import Solid
from kernel.contracts.surface_placement import (
    SurfacePlacement,
)
from kernel.services.extrusion_engine import (
    ExtrusionEngineInterface,
)


@dataclass(frozen=True, slots=True)
class ExtrusionStageResult:
    """
    Immutable result produced by ExtrusionStage.
    """

    solid: Solid


class ExtrusionStage:
    """
    Coordinates the Extrusion Engine.

    The stage performs no CAD operations itself.
    It only validates and orchestrates.
    """

    def __init__(
        self,
        engine: ExtrusionEngineInterface,
    ) -> None:
        self._engine = engine

    def execute(
        self,
        placement: SurfacePlacement,
        profile: ExtrusionProfile,
    ) -> ExtrusionStageResult:
        """
        Executes one extrusion operation.
        """

        placement.validate()
        profile.validate()

        solid = self._engine.extrude(
            placement=placement,
            profile=profile,
        )

        solid.validate()

        return ExtrusionStageResult(
            solid=solid,
        )