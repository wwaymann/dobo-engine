"""
DOBO CAD Kernel

Offset Solid Builder

Builds closed CAD solids from inner and outer
offset contour layers.

This initial implementation supports closed,
convex polygonal contours.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import cadquery as cq

from kernel.contracts.offset_contour import OffsetContour
from kernel.contracts.offset_contour_set import OffsetContourSet
from kernel.contracts.solid import BoundingBox, Solid, SolidValidation

Point3D = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class OffsetSolidBuildResult:
    """Result produced by OffsetSolidBuilder."""

    solid: Solid
    source: OffsetContourSet
    generated_solids: tuple[cq.Shape, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.generated_solids)

    def validate(self) -> None:
        self.source.validate()
        self.solid.validate()

        if not self.generated_solids:
            raise ValueError("OffsetSolidBuildResult cannot be empty.")

        for geometry in self.generated_solids:
            if not isinstance(geometry, cq.Shape):
                raise TypeError(
                    "OffsetSolidBuildResult contains non-CadQuery geometry."
                )
            if not geometry.isValid():
                raise ValueError(
                    "OffsetSolidBuildResult contains invalid CAD geometry."
                )

        if not isinstance(self.metadata, dict):
            raise TypeError("OffsetSolidBuildResult metadata must be a dictionary.")


class OffsetSolidBuilderInterface(ABC):
    """Public interface for offset solid builders."""

    @abstractmethod
    def build(
        self,
        contours: OffsetContourSet,
    ) -> OffsetSolidBuildResult:
        """Builds closed solids from offset contours."""


class OffsetSolidBuilder(OffsetSolidBuilderInterface):
    """
    Builds one faceted BREP Solid per OffsetContour.

    Each solid contains:

    - triangulated inner cap;
    - triangulated outer cap;
    - two triangular side faces per contour segment.

    Current limitation:

    - closed convex contours only.
    """

    def build(
        self,
        contours: OffsetContourSet,
    ) -> OffsetSolidBuildResult:
        contours.validate()

        generated_solids = tuple(
            self._build_contour_solid(contour) for contour in contours.contours
        )

        if not generated_solids:
            raise RuntimeError("OffsetSolidBuilder generated no solids.")

        combined_geometry = self._combine_solids(list(generated_solids))

        solid_contract = self._build_solid_contract(
            geometry=combined_geometry,
            source=contours,
            generated_count=len(generated_solids),
        )

        result = OffsetSolidBuildResult(
            solid=solid_contract,
            source=contours,
            generated_solids=generated_solids,
            metadata={
                "builder": "offset_solid_builder",
                "strategy": "faceted_shell",
                "contour_count": contours.count,
                "point_count": contours.point_count,
                "convex_only": True,
            },
        )
        result.validate()
        return result

    def _build_contour_solid(
        self,
        contour: OffsetContour,
    ) -> cq.Shape:
        contour.validate()

        if not contour.closed:
            raise NotImplementedError(
                "OffsetSolidBuilder currently requires closed contours."
            )

        inner_points = contour.inner_points
        outer_points = contour.outer_points

        if len(inner_points) != len(outer_points):
            raise ValueError("Inner and outer point counts must match.")

        if len(inner_points) < 3:
            raise ValueError(
                "OffsetSolidBuilder requires at least three points per contour."
            )

        inner_center = self._calculate_center(inner_points)
        outer_center = self._calculate_center(outer_points)

        faces: list[cq.Face] = []
        faces.extend(
            self._build_cap_faces(
                points=inner_points,
                center=inner_center,
                reverse=True,
            )
        )
        faces.extend(
            self._build_cap_faces(
                points=outer_points,
                center=outer_center,
                reverse=False,
            )
        )
        faces.extend(
            self._build_side_faces(
                inner_points=inner_points,
                outer_points=outer_points,
            )
        )

        try:
            shell = cq.Shell.makeShell(faces)
            if not isinstance(shell, cq.Shell):
                raise RuntimeError("OffsetSolidBuilder could not create a Shell.")
            geometry = cq.Solid.makeSolid(shell).clean()
        except Exception as error:
            raise RuntimeError(
                "OffsetSolidBuilder could not create a closed Solid "
                "from the generated faces."
            ) from error

        if not isinstance(geometry, cq.Shape):
            raise RuntimeError(
                "OffsetSolidBuilder did not produce CadQuery Shape geometry."
            )
        if not geometry.isValid():
            raise RuntimeError("OffsetSolidBuilder generated invalid CAD geometry.")
        if geometry.Volume() <= 0:
            raise RuntimeError("OffsetSolidBuilder generated zero-volume geometry.")

        return geometry

    def _build_cap_faces(
        self,
        points: tuple[Point3D, ...],
        center: Point3D,
        reverse: bool,
    ) -> list[cq.Face]:
        faces: list[cq.Face] = []
        point_count = len(points)

        for index in range(point_count):
            next_index = (index + 1) % point_count
            current = points[index]
            following = points[next_index]

            triangle = (
                (center, following, current)
                if reverse
                else (center, current, following)
            )
            faces.append(self._build_planar_face(triangle))

        return faces

    def _build_side_faces(
        self,
        inner_points: tuple[Point3D, ...],
        outer_points: tuple[Point3D, ...],
    ) -> list[cq.Face]:
        """
        Builds two triangular side faces for every
        corresponding inner and outer contour segment.

        Cylindrical offset quadrilaterals are generally
        non-planar, so each one is divided diagonally
        into two planar triangles.
        """

        if len(inner_points) != len(outer_points):
            raise ValueError("Inner and outer point counts must match.")

        faces: list[cq.Face] = []
        point_count = len(inner_points)

        for index in range(point_count):
            next_index = (index + 1) % point_count

            inner_current = inner_points[index]
            inner_next = inner_points[next_index]
            outer_current = outer_points[index]
            outer_next = outer_points[next_index]

            first_triangle = (
                inner_current,
                inner_next,
                outer_next,
            )
            second_triangle = (
                inner_current,
                outer_next,
                outer_current,
            )

            faces.append(self._build_planar_face(first_triangle))
            faces.append(self._build_planar_face(second_triangle))

        return faces

    @staticmethod
    def _build_planar_face(
        points: tuple[Point3D, ...],
    ) -> cq.Face:
        if len(points) < 3:
            raise ValueError(
                "OffsetSolidBuilder requires at least three points per Face."
            )

        vectors = [cq.Vector(*point) for point in points]
        wire = cq.Wire.makePolygon(vectors, close=True)

        if not isinstance(wire, cq.Wire):
            raise RuntimeError("OffsetSolidBuilder could not create a face Wire.")
        if not wire.isValid():
            raise RuntimeError("OffsetSolidBuilder created an invalid face Wire.")

        try:
            face = cq.Face.makeFromWires(wire)
        except Exception as error:
            raise RuntimeError(
                "OffsetSolidBuilder could not create a planar Face."
            ) from error

        if not isinstance(face, cq.Face):
            raise RuntimeError("OffsetSolidBuilder did not create a CadQuery Face.")
        if not face.isValid():
            raise RuntimeError("OffsetSolidBuilder created an invalid Face.")

        return face

    @staticmethod
    def _calculate_center(
        points: tuple[Point3D, ...],
    ) -> Point3D:
        if not points:
            raise ValueError("Cannot calculate the center of an empty contour.")

        count = float(len(points))
        return (
            sum(point[0] for point in points) / count,
            sum(point[1] for point in points) / count,
            sum(point[2] for point in points) / count,
        )

    @staticmethod
    def _combine_solids(
        solids: list[cq.Shape],
    ) -> cq.Shape:
        if not solids:
            raise ValueError("OffsetSolidBuilder requires at least one Solid.")

        if len(solids) == 1:
            return solids[0]

        try:
            geometry = solids[0].fuse(*solids[1:]).clean()
        except Exception as error:
            raise RuntimeError(
                "OffsetSolidBuilder could not combine the generated solids."
            ) from error

        if not isinstance(geometry, cq.Shape):
            raise RuntimeError(
                "OffsetSolidBuilder combined result is not CadQuery geometry."
            )
        if not geometry.isValid():
            raise RuntimeError("OffsetSolidBuilder combined result is invalid.")

        return geometry

    @staticmethod
    def _build_solid_contract(
        geometry: cq.Shape,
        source: OffsetContourSet,
        generated_count: int,
    ) -> Solid:
        volume = float(geometry.Volume())

        if volume <= 0:
            raise RuntimeError(
                "OffsetSolidBuilder final volume must be greater than zero."
            )

        center = geometry.Center()
        box = geometry.BoundingBox()

        result = Solid(
            geometry=geometry,
            volume=volume,
            center_of_mass=(
                float(center.x),
                float(center.y),
                float(center.z),
            ),
            bounding_box=BoundingBox(
                minimum=(
                    float(box.xmin),
                    float(box.ymin),
                    float(box.zmin),
                ),
                maximum=(
                    float(box.xmax),
                    float(box.ymax),
                    float(box.zmax),
                ),
            ),
            validation=SolidValidation(
                is_valid=bool(geometry.isValid()),
                is_closed=True,
                is_manifold=True,
                is_watertight=True,
                errors=(),
                warnings=(),
            ),
            source="offset_solid_builder",
            metadata={
                "strategy": "faceted_shell",
                "generated_solid_count": generated_count,
                "contour_count": source.count,
                "point_count": source.point_count,
                "offset_distance": source.metadata.get("distance"),
                "surface_type": source.metadata.get("surface_type"),
                "convex_only": True,
            },
        )
        result.validate()
        return result
