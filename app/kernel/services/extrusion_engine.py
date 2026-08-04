"""
DOBO CAD Kernel

Extrusion Engine

Converts a SurfacePlacement into valid solid geometry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import cadquery as cq

from kernel.contracts.extrusion_profile import (
    ExtrusionMode,
    ExtrusionProfile,
)
from kernel.contracts.solid import (
    BoundingBox,
    Solid,
    SolidValidation,
)
from kernel.contracts.surface_placement import (
    SurfacePlacement,
)


class ExtrusionEngineInterface(ABC):
    """
    Public interface implemented by Extrusion Engines.
    """

    @abstractmethod
    def extrude(
        self,
        placement: SurfacePlacement,
        profile: ExtrusionProfile,
    ) -> Solid:
        """
        Creates solid geometry from SurfacePlacement.
        """


class ExtrusionEngine(ExtrusionEngineInterface):
    """
    Initial Extrusion Engine implementation.

    Current support:

    - Normal extrusion
    - Rigid planar SurfacePlacement

    Future support:

    - Bidirectional extrusion
    - Directional extrusion
    - Segmented surface extrusion
    - Sweep
    - Loft
    - Revolve
    """

    def extrude(
        self,
        placement: SurfacePlacement,
        profile: ExtrusionProfile,
    ) -> Solid:
        """
        Converts placed contours into a Solid.
        """

        placement.validate()
        profile.validate()

        if profile.mode != ExtrusionMode.NORMAL:
            raise NotImplementedError(
                "The initial ExtrusionEngine only "
                "supports normal extrusion."
            )

        if not placement.local_coordinate_systems:
            raise ValueError(
                "Normal extrusion requires at least one "
                "local coordinate system."
            )

        normal = (
            placement
            .local_coordinate_systems[0]
            .normal
        )

        direction = cq.Vector(
            normal[0] * profile.depth,
            normal[1] * profile.depth,
            normal[2] * profile.depth,
        )

        generated_solids: list[cq.Shape] = []

        for contour in (
            placement.placed_contours.contours
        ):
            geometry = contour.geometry

            if not isinstance(
                geometry,
                cq.Wire,
            ):
                raise TypeError(
                    "The initial ExtrusionEngine requires "
                    "Contour geometry to be a CadQuery Wire."
                )

            face = cq.Face.makeFromWires(
                geometry
            )

            generated_shape = (
                cq.Solid.extrudeLinear(
                    face,
                    direction,
                )
            )

            if not isinstance(
                generated_shape,
                cq.Shape,
            ):
                raise RuntimeError(
                    "ExtrusionEngine could not generate "
                    "solid geometry."
                )

            generated_solids.append(
                generated_shape
            )

        if not generated_solids:
            raise RuntimeError(
                "ExtrusionEngine generated no solids."
            )

        result_geometry = self._combine_solids(
            generated_solids
        )

        volume = float(
            result_geometry.Volume()
        )

        center = (
            result_geometry.Center()
        )

        bounding_box = (
            result_geometry.BoundingBox()
        )

        validation = SolidValidation(
            is_valid=result_geometry.isValid(),
            is_closed=True,
            is_manifold=True,
            is_watertight=True,
            errors=(),
            warnings=(),
        )

        result = Solid(
            geometry=result_geometry,
            volume=volume,
            center_of_mass=(
                float(center.x),
                float(center.y),
                float(center.z),
            ),
            bounding_box=BoundingBox(
                minimum=(
                    float(bounding_box.xmin),
                    float(bounding_box.ymin),
                    float(bounding_box.zmin),
                ),
                maximum=(
                    float(bounding_box.xmax),
                    float(bounding_box.ymax),
                    float(bounding_box.zmax),
                ),
            ),
            validation=validation,
            source="extrusion_engine",
            metadata={
                "mode": profile.mode.value,
                "depth": profile.depth,
                "contour_count": (
                    placement.placed_contours.count
                ),
            },
        )

        result.validate()

        return result

    @staticmethod
    def _combine_solids(
        solids: list[cq.Shape],
    ) -> cq.Shape:
        """
        Combines multiple generated solids.

        A single solid is returned directly.
        Multiple solids are fused in one operation.
        """

        if len(solids) == 1:
            return solids[0]

        base_shape = solids[0]

        try:
            combined_shape = base_shape.fuse(
                *solids[1:]
            )

        except Exception as error:
            raise RuntimeError(
                "ExtrusionEngine could not combine "
                "the generated solids."
            ) from error

        if not isinstance(
            combined_shape,
            cq.Shape,
        ):
            raise RuntimeError(
                "ExtrusionEngine produced an invalid "
                "combined geometry object."
            )

        return combined_shape