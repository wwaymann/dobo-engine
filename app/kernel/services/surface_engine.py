"""
DOBO CAD Kernel

Surface Engine

Supports rigid placement on:

- Plane
- Cylinder
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any, cast

import cadquery as cq

from kernel.contracts.contour import Contour
from kernel.contracts.contour_set import ContourSet
from kernel.contracts.placement import Placement
from kernel.contracts.surface import Surface, SurfaceType
from kernel.contracts.surface_placement import (
    LocalCoordinateSystem,
    PlacementQuality,
    SurfacePlacement,
)

Vector3 = tuple[float, float, float]
Point2D = tuple[float, float]


class SurfaceEngineInterface(ABC):
    @abstractmethod
    def place(
        self,
        contours: ContourSet,
        placement: Placement,
        surface: Surface,
    ) -> SurfacePlacement:
        """Adapts a ContourSet to a target Surface."""


class SurfaceEngine(SurfaceEngineInterface):
    def place(
        self,
        contours: ContourSet,
        placement: Placement,
        surface: Surface,
    ) -> SurfacePlacement:
        if contours.is_empty:
            raise ValueError("SurfaceEngine requires a non-empty ContourSet.")

        if not contours.validate():
            raise ValueError("SurfaceEngine received invalid Contours.")

        placement.validate()
        surface.validate()

        if surface.type == SurfaceType.PLANE:
            return self._place_on_plane(
                contours=contours,
                placement=placement,
                surface=surface,
            )

        if surface.type == SurfaceType.CYLINDER:
            return self._place_on_cylinder(
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
        plane_origin = self._read_vector3(
            surface.parameters.get("origin", (0.0, 0.0, 0.0)),
            parameter_name="origin",
        )
        plane_normal = self._read_vector3(
            surface.parameters.get("normal", (0.0, 0.0, 1.0)),
            parameter_name="normal",
        )

        if not self._is_positive_z_normal(plane_normal):
            raise NotImplementedError(
                "The initial Plane SurfaceEngine only " "supports normal (0, 0, 1)."
            )

        self._validate_uniform_xy_scale(placement)

        translation = (
            plane_origin[0] + placement.position[0],
            plane_origin[1] + placement.position[1],
            plane_origin[2] + placement.position[2],
        )
        rotation_degrees = placement.rotation[2]
        scale_factor = placement.scale[0]

        transformed_contours: list[Contour] = []

        for contour in contours.contours:
            transformed_geometry = self._transform_planar_geometry(
                geometry=contour.geometry,
                translation=translation,
                rotation_z=rotation_degrees,
                scale_factor=scale_factor,
            )
            transformed_contours.append(
                Contour(
                    geometry=transformed_geometry,
                    source=contour.source,
                    metadata={
                        **contour.metadata,
                        "surface_type": surface.type.value,
                        "translation": translation,
                        "rotation_degrees": rotation_degrees,
                        "scale": scale_factor,
                    },
                )
            )

        placed_contours = ContourSet(
            contours=transformed_contours,
            source=contours.source,
            metadata={
                **contours.metadata,
                "surface": surface.type.value,
            },
        )

        coordinate_system = LocalCoordinateSystem(
            origin=translation,
            x_axis=(1.0, 0.0, 0.0),
            y_axis=(0.0, 1.0, 0.0),
            normal=(0.0, 0.0, 1.0),
        )

        return self._build_surface_placement(
            source_contours=contours,
            placed_contours=placed_contours,
            surface=surface,
            placement=placement,
            coordinate_system=coordinate_system,
            metadata={"strategy": "rigid"},
        )

    def _place_on_cylinder(
        self,
        contours: ContourSet,
        placement: Placement,
        surface: Surface,
    ) -> SurfacePlacement:
        self._validate_uniform_xy_scale(placement)

        radius = self._read_positive_float(
            surface.parameters.get("radius"),
            parameter_name="radius",
        )
        height = self._read_positive_float(
            surface.parameters.get("height"),
            parameter_name="height",
        )
        samples_per_edge = self._read_positive_int(
            surface.parameters.get("samples_per_edge", 32),
            parameter_name="samples_per_edge",
        )
        cylinder_origin = self._read_vector3(
            surface.parameters.get("origin", (0.0, 0.0, 0.0)),
            parameter_name="origin",
        )

        angle_degrees = (
            placement.angle_degrees if placement.angle_degrees is not None else 0.0
        )
        position_z = placement.position[2]

        if position_z < 0.0 or position_z > height:
            raise ValueError(
                "Cylinder placement position.z must " "be inside the cylinder height."
            )

        angle_radians = math.radians(angle_degrees)

        radial: Vector3 = (
            math.sin(angle_radians),
            math.cos(angle_radians),
            0.0,
        )
        normal = self._normalize_vector(radial)
        tangent = self._normalize_vector((-normal[1], normal[0], 0.0))
        vertical: Vector3 = (0.0, 0.0, 1.0)

        surface_point = (
            cylinder_origin[0] + radius * normal[0],
            cylinder_origin[1] + radius * normal[1],
            cylinder_origin[2] + position_z,
        )

        radial_offset = placement.position[0]
        vertical_offset = placement.position[1]

        plane_origin = (
            surface_point[0]
            + normal[0] * radial_offset
            + vertical[0] * vertical_offset,
            surface_point[1]
            + normal[1] * radial_offset
            + vertical[1] * vertical_offset,
            surface_point[2]
            + normal[2] * radial_offset
            + vertical[2] * vertical_offset,
        )

        rotation_degrees = placement.rotation[2]
        rotated_x_axis = self._rotate_axis_in_plane(
            horizontal=tangent,
            vertical=vertical,
            rotation_degrees=rotation_degrees,
        )
        rotated_y_axis = self._cross_product(
            normal,
            rotated_x_axis,
        )

        tangent_plane = cq.Plane(
            origin=plane_origin,
            xDir=rotated_x_axis,
            normal=normal,
        )

        scale_factor = placement.scale[0]
        transformed_contours: list[Contour] = []

        for contour in contours.contours:
            local_points = self._sample_wire_points(
                geometry=contour.geometry,
                samples_per_edge=samples_per_edge,
            )
            scaled_points = [
                (
                    point[0] * scale_factor,
                    point[1] * scale_factor,
                )
                for point in local_points
            ]
            transformed_geometry = self._build_wire_on_plane(
                points=scaled_points,
                plane=tangent_plane,
            )
            transformed_contours.append(
                Contour(
                    geometry=transformed_geometry,
                    source=contour.source,
                    metadata={
                        **contour.metadata,
                        "surface_type": surface.type.value,
                        "radius": radius,
                        "height": height,
                        "angle_degrees": angle_degrees,
                        "position_z": position_z,
                        "rotation_degrees": rotation_degrees,
                        "scale": scale_factor,
                        "samples_per_edge": samples_per_edge,
                        "placement_strategy": "rigid",
                    },
                )
            )

        placed_contours = ContourSet(
            contours=transformed_contours,
            source=contours.source,
            metadata={
                **contours.metadata,
                "surface": surface.type.value,
                "angle_degrees": angle_degrees,
                "position_z": position_z,
            },
        )

        coordinate_system = LocalCoordinateSystem(
            origin=plane_origin,
            x_axis=(
                float(rotated_x_axis[0]),
                float(rotated_x_axis[1]),
                float(rotated_x_axis[2]),
            ),
            y_axis=(
                float(rotated_y_axis[0]),
                float(rotated_y_axis[1]),
                float(rotated_y_axis[2]),
            ),
            normal=(
                float(normal[0]),
                float(normal[1]),
                float(normal[2]),
            ),
        )

        return self._build_surface_placement(
            source_contours=contours,
            placed_contours=placed_contours,
            surface=surface,
            placement=placement,
            coordinate_system=coordinate_system,
            metadata={
                "strategy": "rigid",
                "angle_degrees": angle_degrees,
                "position_z": position_z,
                "radius": radius,
            },
        )

    @staticmethod
    def _build_surface_placement(
        source_contours: ContourSet,
        placed_contours: ContourSet,
        surface: Surface,
        placement: Placement,
        coordinate_system: LocalCoordinateSystem,
        metadata: dict[str, object],
    ) -> SurfacePlacement:
        result = SurfacePlacement(
            source_contours=source_contours,
            placed_contours=placed_contours,
            surface=surface,
            placement=placement,
            local_coordinate_systems=(coordinate_system,),
            quality=PlacementQuality(strategy="rigid"),
            metadata={
                "engine": "surface",
                "surface_type": surface.type.value,
                **metadata,
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
        if not isinstance(geometry, cq.Shape):
            raise TypeError("SurfaceEngine requires CadQuery Shape geometry.")

        transformed = geometry

        if scale_factor != 1.0:
            transformed = transformed.scale(scale_factor)

        if rotation_z != 0.0:
            transformed = transformed.rotate(
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                rotation_z,
            )

        if translation != (0.0, 0.0, 0.0):
            transformed = transformed.translate(translation)

        if not isinstance(transformed, cq.Shape):
            raise RuntimeError(
                "SurfaceEngine could not transform the Contour geometry."
            )

        return transformed

    @staticmethod
    def _sample_wire_points(
        geometry: object,
        samples_per_edge: int,
    ) -> list[Point2D]:
        if not isinstance(geometry, cq.Wire):
            raise TypeError(
                "Cylinder placement requires Contour geometry " "to be a CadQuery Wire."
            )

        points: list[Point2D] = []
        edges = geometry.Edges()

        if not edges:
            raise ValueError("Cylinder placement received a Wire without edges.")

        for edge_index, edge in enumerate(edges):
            typed_edge = cast(Any, edge)
            edge_points = [
                typed_edge.positionAt(sample_index / samples_per_edge)
                for sample_index in range(samples_per_edge)
            ]

            for point_index, point in enumerate(edge_points):
                if edge_index > 0 and point_index == 0:
                    continue

                points.append(
                    (
                        float(point.x),
                        float(point.y),
                    )
                )

        if len(points) < 3:
            raise ValueError(
                "Cylinder placement requires at least " "three sampled contour points."
            )

        return points

    @staticmethod
    def _build_wire_on_plane(
        points: list[Point2D],
        plane: cq.Plane,
    ) -> cq.Wire:
        workplane = cq.Workplane(plane).polyline(points).close()
        geometry = workplane.val()

        if not isinstance(geometry, cq.Wire):
            raise RuntimeError("SurfaceEngine could not build the tangent Wire.")

        if not geometry.isValid():
            raise RuntimeError("SurfaceEngine created an invalid tangent Wire.")

        return geometry

    @staticmethod
    def _rotate_axis_in_plane(
        horizontal: Vector3,
        vertical: Vector3,
        rotation_degrees: float,
    ) -> Vector3:
        angle_radians = math.radians(rotation_degrees)
        cosine = math.cos(angle_radians)
        sine = math.sin(angle_radians)

        return SurfaceEngine._normalize_vector(
            (
                horizontal[0] * cosine + vertical[0] * sine,
                horizontal[1] * cosine + vertical[1] * sine,
                horizontal[2] * cosine + vertical[2] * sine,
            )
        )

    @staticmethod
    def _cross_product(
        first: Vector3,
        second: Vector3,
    ) -> Vector3:
        return SurfaceEngine._normalize_vector(
            (
                first[1] * second[2] - first[2] * second[1],
                first[2] * second[0] - first[0] * second[2],
                first[0] * second[1] - first[1] * second[0],
            )
        )

    @staticmethod
    def _normalize_vector(
        vector: Vector3,
    ) -> Vector3:
        length = math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)

        if length <= 0:
            raise ValueError("Cannot normalize a zero-length vector.")

        return (
            vector[0] / length,
            vector[1] / length,
            vector[2] / length,
        )

    @staticmethod
    def _read_vector3(
        value: object,
        parameter_name: str,
    ) -> Vector3:
        if not isinstance(value, (tuple, list)):
            raise ValueError(
                f"Surface {parameter_name} must contain " "three numeric values."
            )

        if len(value) != 3:
            raise ValueError(
                f"Surface {parameter_name} must contain " "exactly three values."
            )

        raw_values = (
            value[0],
            value[1],
            value[2],
        )

        if not all(
            isinstance(item, (int, float, str)) and not isinstance(item, bool)
            for item in raw_values
        ):
            raise ValueError(f"Surface {parameter_name} values must be numeric.")

        try:
            return (
                float(raw_values[0]),
                float(raw_values[1]),
                float(raw_values[2]),
            )

        except ValueError as error:
            raise ValueError(
                f"Surface {parameter_name} values must be numeric."
            ) from error

    @staticmethod
    def _read_positive_float(
        value: object,
        parameter_name: str,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float, str),
        ):
            raise ValueError(f"Surface {parameter_name} must be numeric.")

        try:
            result = float(value)
        except ValueError as error:
            raise ValueError(f"Surface {parameter_name} must be numeric.") from error

        if result <= 0:
            raise ValueError(f"Surface {parameter_name} must be greater than zero.")

        return result

    @staticmethod
    def _read_positive_int(
        value: object,
        parameter_name: str,
    ) -> int:
        if isinstance(value, bool):
            raise ValueError(f"Surface {parameter_name} must be an integer.")

        if not isinstance(value, (int, float, str)):
            raise ValueError(f"Surface {parameter_name} must be numeric.")

        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"Surface {parameter_name} must be a whole number.")

        if isinstance(value, str):
            normalized_value = value.strip()

            if not normalized_value:
                raise ValueError(f"Surface {parameter_name} cannot be empty.")

            try:
                numeric_value = float(normalized_value)
            except ValueError as error:
                raise ValueError(
                    f"Surface {parameter_name} must be numeric."
                ) from error

            if not numeric_value.is_integer():
                raise ValueError(f"Surface {parameter_name} must be a whole number.")

        try:
            result = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Surface {parameter_name} must be an integer.") from error

        if result < 4:
            raise ValueError(f"Surface {parameter_name} must be at least 4.")

        return result

    @staticmethod
    def _validate_uniform_xy_scale(
        placement: Placement,
    ) -> None:
        if placement.scale[0] != placement.scale[1]:
            raise NotImplementedError(
                "SurfaceEngine currently supports uniform XY scaling only."
            )

    @staticmethod
    def _is_positive_z_normal(
        normal: Vector3,
        tolerance: float = 1e-9,
    ) -> bool:
        return (
            abs(normal[0]) <= tolerance
            and abs(normal[1]) <= tolerance
            and abs(normal[2] - 1.0) <= tolerance
        )
