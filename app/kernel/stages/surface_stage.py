"""
DOBO CAD Kernel

Surface Stage

Coordinates the Surface Engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernel.contracts.contour_set import ContourSet
from kernel.contracts.placement import Placement
from kernel.contracts.surface import Surface
from kernel.contracts.surface_placement import SurfacePlacement
from kernel.services.surface_engine import SurfaceEngineInterface


@dataclass(frozen=True, slots=True)
class SurfaceStageResult:
    """
    Immutable result produced by SurfaceStage.
    """

    placement: SurfacePlacement


class SurfaceStage:
    """
    Coordinates the Surface Engine.

    This stage contains no geometry algorithms.
    """

    def __init__(
        self,
        engine: SurfaceEngineInterface,
    ) -> None:
        self._engine = engine

    def execute(
        self,
        contours: ContourSet,
        placement: Placement,
        surface: Surface,
    ) -> SurfaceStageResult:
        """
        Executes one surface-adaptation operation.
        """

        result = self._engine.place(
            contours=contours,
            placement=placement,
            surface=surface,
        )

        result.validate()

        return SurfaceStageResult(
            placement=result,
        )