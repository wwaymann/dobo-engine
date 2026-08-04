"""
DOBO CAD Kernel

Surface Engine

Initial implementation supporting planar placement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import cadquery as cq

from kernel.contracts.contour import Contour
from kernel.contracts.contour_set import ContourSet
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.contracts.surface_placement import (
    LocalCoordinateSystem,
    PlacementQuality,
    SurfacePlacement,
)


Vector3 = tuple[float, float, float]


class SurfaceEngineInterface(ABC):
    """
    Public interface implemented by Surface Engines.
    """

    @abstractmethod
    def place(
        self,
        contours: ContourSet,
        placement: Placement,
        surface: Surface,
    ) -> SurfacePlacement:
        """
        Adapts a ContourSet to a target Surface.
        """


class SurfaceEngine(SurfaceEngineInterface):
    """
    Initial Surface Engine implementation.

    Current support:

    - Plane

    Future support:

    - Cylinder
    - Cone
    - Sphere
    - Mesh
    """

    def place(
        self,
        contours: ContourSet,
        placement: Placement,
        surface: Surface,
    ) -> SurfacePlacement:
        """
        Places a ContourSet on the supplied Surface.
        """

        if contours.is_empty:
            raise ValueError(
                "SurfaceEngine requires a non-empty ContourSet."
            )

        if not contours.validate():
            raise ValueError(
                "SurfaceEngine received invalid Contours."
            )

        placement.validate()
        surface.validate()

        if surface.type == SurfaceType.PLANE:
            return self._place_on_plane(
                contours=contours,
                placement=placement,
                surface=surface,
            )

        raise NotImplementedError(
            "SurfaceEngine does not yet support "
            f"surface type '{surface.type.value}'."
        )

    def _place_on_plane(
        self,
        contours: ContourSet,
        placement: Placement,
        surface: Surface,
    ) -> SurfacePlacement:
        """
        Places geometry on a planar surface.

        This first implementation supports a plane
        parallel to XY with normal (0, 0, 1).
        """

        plane_origin = self._read_vector3(
            surface.parameters.get(
                "origin",
                (0.0, 0.0, 0.0),
            ),
            parameter_name="origin",
        )

        plane_normal = self._read_vector3(
            surface.parameters.get(
                "normal",
                (0.0, 0.0, 1.0),
            ),
            parameter_name="normal",
        )

        if not self._is_positive_z_normal(
            plane_normal
        ):
            raise NotImplementedError(
                "The initial Plane SurfaceEngine only "
                "supports normal (0, 0, 1)."
            )

        if (
            placement.scale[0]
            != placement.scale[1]
        ):
            raise NotImplementedError(
                "The initial Plane SurfaceEngine only "
                "supports uniform XY scaling."
            )

        transformed_contours: list[Contour] = []

        translation = (
            plane_origin[0]
            + placement.position[0],
            plane_origin[1]
            + placement.position[1],
            plane_origin[2]
            + placement.position[2],
        )

        rotation_z = placement.rotation[2]

        scale_factor = placement.scale[0]

        for contour in contours.contours:
            transformed_geometry = (
                self._transform_planar_geometry(
                    geometry=contour.geometry,
                    translation=translation,
                    rotation_z=rotation_z,
                    scale_factor=scale_factor,
                )
            )

            transformed_contours.append(
                Contour(
                    geometry=transformed_geometry,
                    source=contour.source,
                    metadata={
                        **contour.metadata,
                        "surface_type": (
                            surface.type.value
                        ),
                        "translation": translation,
                        "rotation_z": rotation_z,
                        "scale": scale_factor,
                    },
                )
            )

        placed_contour_set = ContourSet(
            contours=transformed_contours,
            source=contours.source,
            metadata={
                **contours.metadata,
                "surface": surface.type.value,
            },
        )

        local_coordinate_system = (
            LocalCoordinateSystem(
                origin=translation,
                x_axis=(
                    1.0,
                    0.0,
                    0.0,
                ),
                y_axis=(
                    0.0,
                    1.0,
                    0.0,
                ),
                normal=(
                    0.0,
                    0.0,
                    1.0,
                ),
            )
        )

        result = SurfacePlacement(
            source_contours=contours,
            placed_contours=placed_contour_set,
            surface=surface,
            placement=placement,
            local_coordinate_systems=(
                local_coordinate_system,
            ),
            quality=PlacementQuality(
                strategy="rigid",
            ),
            metadata={
                "engine": "surface",
                "surface_type": (
                    surface.type.value
                ),
            },
        )

        result.validate()

        return result

    @staticmethod
    def _transform_planar_geometry(
        geometry: object,
        translation: Vector3,
        rotation_z: float,
        scale_factor: float,
    ) -> cq.Shape:
        """
        Applies planar scale, rotation and translation
        to backend geometry.
        """

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise TypeError(
                "The initial SurfaceEngine requires "
                "CadQuery Shape geometry."
            )

        transformed = geometry

        if scale_factor != 1.0:
            transformed = transformed.scale(
                scale_factor
            )

        if rotation_z != 0.0:
            transformed = transformed.rotate(
                (
                    0.0,
                    0.0,
                    0.0,
                ),
                (
                    0.0,
                    0.0,
                    1.0,
                ),
                rotation_z,
            )

        if translation != (
            0.0,
            0.0,
            0.0,
        ):
            transformed = transformed.translate(
                translation
            )

        if not isinstance(
            transformed,
            cq.Shape,
        ):
            raise RuntimeError(
                "SurfaceEngine could not transform "
                "the Contour geometry."
            )

        return transformed

    @staticmethod
    def _read_vector3(
        value: object,
        parameter_name: str,
    ) -> Vector3:
        """
        Reads and validates a three-dimensional vector.
        """

        if not isinstance(
            value,
            (
                tuple,
                list,
            ),
        ):
            raise ValueError(
                f"Surface {parameter_name} must "
                "contain three numeric values."
            )

        if len(value) != 3:
            raise ValueError(
                f"Surface {parameter_name} must "
                "contain exactly three values."
            )

        try:
            return (
                float(value[0]),
                float(value[1]),
                float(value[2]),
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                f"Surface {parameter_name} values "
                "must be numeric."
            ) from error

    @staticmethod
    def _is_positive_z_normal(
        normal: Vector3,
        tolerance: float = 1e-9,
    ) -> bool:
        """
        Returns whether the normal points along +Z.
        """

        return (
            abs(normal[0]) <= tolerance
            and abs(normal[1]) <= tolerance
            and abs(normal[2] - 1.0)
            <= tolerance
        )