"""
DOBO CAD Kernel

Geometry Projection Engine

Transforms backend-independent two-dimensional contour
definitions into backend-independent projected 3D contours.

This service contains mathematical projection only.
It must not import CadQuery or OpenCascade.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from kernel.contracts.contour_definition_set import (
    ContourDefinitionSet,
)
from kernel.contracts.placement import Placement
from kernel.contracts.projected_contour import (
    ProjectedContour,
)
from kernel.contracts.projected_contour_set import (
    ProjectedContourSet,
)
from kernel.contracts.projected_point import (
    ProjectedPoint,
)
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)


Vector3 = tuple[float, float, float]
Point2D = tuple[float, float]


class GeometryProjectionEngineInterface(ABC):
    """
    Public interface for mathematical projection engines.
    """

    @abstractmethod
    def project(
        self,
        contours: ContourDefinitionSet,
        placement: Placement,
        surface: Surface,
    ) -> ProjectedContourSet:
        """
        Projects two-dimensional contours onto a surface.
        """


class GeometryProjectionEngine(
    GeometryProjectionEngineInterface,
):
    """
    Projects pure 2D geometry into pure 3D geometry.

    Current support:

    - Plane
    - Cylinder
    """

    def project(
        self,
        contours: ContourDefinitionSet,
        placement: Placement,
        surface: Surface,
    ) -> ProjectedContourSet:
        """
        Projects a complete ContourDefinitionSet.
        """

        contours.validate()
        placement.validate()
        surface.validate()

        self._validate_uniform_xy_scale(
            placement
        )

        if surface.type == SurfaceType.PLANE:
            return self._project_on_plane(
                contours=contours,
                placement=placement,
                surface=surface,
            )

        if surface.type == SurfaceType.CYLINDER:
            return self._project_on_cylinder(
                contours=contours,
                placement=placement,
                surface=surface,
            )

        raise NotImplementedError(
            "GeometryProjectionEngine does not yet "
            f"support surface type '{surface.type.value}'."
        )

    def _project_on_plane(
        self,
        contours: ContourDefinitionSet,
        placement: Placement,
        surface: Surface,
    ) -> ProjectedContourSet:
        """
        Projects contours onto a plane parallel to XY.
        """

        origin = self._read_vector3(
            surface.parameters.get(
                "origin",
                (
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
            parameter_name="origin",
        )

        normal = self._read_vector3(
            surface.parameters.get(
                "normal",
                (
                    0.0,
                    0.0,
                    1.0,
                ),
            ),
            parameter_name="normal",
        )

        if not self._is_positive_z_normal(
            normal
        ):
            raise NotImplementedError(
                "Plane projection currently supports "
                "normal (0, 0, 1) only."
            )

        normalized_normal = (
            self._normalize_vector(
                normal
            )
        )

        rotation_degrees = (
            placement.rotation[2]
        )

        scale = (
            placement.scale[0]
        )

        translation = (
            origin[0]
            + placement.position[0],
            origin[1]
            + placement.position[1],
            origin[2]
            + placement.position[2],
        )

        projected_contours: list[
            ProjectedContour
        ] = []

        for contour in contours.contours:
            projected_points = tuple(
                self._project_plane_point(
                    point=point,
                    translation=translation,
                    rotation_degrees=(
                        rotation_degrees
                    ),
                    scale=scale,
                )
                for point in contour.points
            )

            projected_normals = tuple(
                normalized_normal
                for _ in projected_points
            )

            projected_contour = (
                ProjectedContour(
                    points=projected_points,
                    closed=contour.closed,
                    normals=projected_normals,
                    metadata={
                        **contour.metadata,
                        "source_contour_id": (
                            contour.id
                        ),
                        "surface_type": (
                            surface.type.value
                        ),
                        "projection_strategy": (
                            "plane"
                        ),
                    },
                )
            )

            projected_contour.validate()

            projected_contours.append(
                projected_contour
            )

        result = ProjectedContourSet(
            contours=tuple(
                projected_contours
            ),
            metadata={
                **contours.metadata,
                "surface_type": (
                    surface.type.value
                ),
                "projection_strategy": (
                    "plane"
                ),
                "origin": origin,
                "normal": normalized_normal,
                "rotation_degrees": (
                    rotation_degrees
                ),
                "scale": scale,
            },
        )

        result.validate()

        return result

    def _project_on_cylinder(
        self,
        contours: ContourDefinitionSet,
        placement: Placement,
        surface: Surface,
    ) -> ProjectedContourSet:
        """
        Wraps contours around a cylindrical surface.

        Local 2D convention:

        - local X is arc length around the cylinder;
        - local Y is vertical displacement.

        Placement convention:

        - angle_degrees selects the angular center;
        - position.z selects the vertical center;
        - position.x is a radial offset;
        - position.y is an additional vertical offset;
        - rotation.z rotates points before projection.
        """

        radius = self._read_positive_float(
            surface.parameters.get(
                "radius"
            ),
            parameter_name="radius",
        )

        height = self._read_positive_float(
            surface.parameters.get(
                "height"
            ),
            parameter_name="height",
        )

        origin = self._read_vector3(
            surface.parameters.get(
                "origin",
                (
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
            parameter_name="origin",
        )

        angle_degrees = (
            placement.angle_degrees
            if placement.angle_degrees
            is not None
            else 0.0
        )

        center_angle_radians = math.radians(
            angle_degrees
        )

        center_z = (
            origin[2]
            + placement.position[2]
            + placement.position[1]
        )

        radial_offset = (
            placement.position[0]
        )

        effective_radius = (
            radius
            + radial_offset
        )

        if effective_radius <= 0:
            raise ValueError(
                "Cylinder effective radius must "
                "be greater than zero."
            )

        rotation_degrees = (
            placement.rotation[2]
        )

        scale = (
            placement.scale[0]
        )

        projected_contours: list[
            ProjectedContour
        ] = []

        for contour in contours.contours:
            projected_points = tuple(
                self._project_cylinder_point(
                    point=point,
                    origin=origin,
                    radius=effective_radius,
                    center_angle_radians=(
                        center_angle_radians
                    ),
                    center_z=center_z,
                    rotation_degrees=(
                        rotation_degrees
                    ),
                    scale=scale,
                )
                for point in contour.points
            )

            minimum_z = min(
                point.z
                for point in projected_points
            )

            maximum_z = max(
                point.z
                for point in projected_points
            )

            cylinder_minimum_z = (
                origin[2]
            )

            cylinder_maximum_z = (
                origin[2]
                + height
            )

            if (
                minimum_z
                < cylinder_minimum_z
                or maximum_z
                > cylinder_maximum_z
            ):
                raise ValueError(
                    "Projected contour exceeds "
                    "the cylinder height."
                )

            projected_normals = tuple(
                self._cylinder_point_normal(
                    point=point,
                    origin=origin,
                )
                for point in projected_points
            )

            projected_contour = (
                ProjectedContour(
                    points=projected_points,
                    closed=contour.closed,
                    normals=projected_normals,
                    metadata={
                        **contour.metadata,
                        "source_contour_id": (
                            contour.id
                        ),
                        "surface_type": (
                            surface.type.value
                        ),
                        "projection_strategy": (
                            "wrapped"
                        ),
                        "radius": radius,
                        "effective_radius": (
                            effective_radius
                        ),
                        "height": height,
                        "angle_degrees": (
                            angle_degrees
                        ),
                    },
                )
            )

            projected_contour.validate()

            projected_contours.append(
                projected_contour
            )

        result = ProjectedContourSet(
            contours=tuple(
                projected_contours
            ),
            metadata={
                **contours.metadata,
                "surface_type": (
                    surface.type.value
                ),
                "projection_strategy": (
                    "wrapped"
                ),
                "radius": radius,
                "effective_radius": (
                    effective_radius
                ),
                "height": height,
                "origin": origin,
                "angle_degrees": (
                    angle_degrees
                ),
                "rotation_degrees": (
                    rotation_degrees
                ),
                "scale": scale,
            },
        )

        result.validate()

        return result

    @staticmethod
    def _project_plane_point(
        point: Point2D,
        translation: Vector3,
        rotation_degrees: float,
        scale: float,
    ) -> ProjectedPoint:
        """
        Applies scale, planar rotation and translation.
        """

        local_x = (
            point[0]
            * scale
        )

        local_y = (
            point[1]
            * scale
        )

        rotated_x, rotated_y = (
            GeometryProjectionEngine
            ._rotate_point_2d(
                x=local_x,
                y=local_y,
                rotation_degrees=(
                    rotation_degrees
                ),
            )
        )

        return ProjectedPoint(
            x=(
                translation[0]
                + rotated_x
            ),
            y=(
                translation[1]
                + rotated_y
            ),
            z=translation[2],
        )

    @staticmethod
    def _project_cylinder_point(
        point: Point2D,
        origin: Vector3,
        radius: float,
        center_angle_radians: float,
        center_z: float,
        rotation_degrees: float,
        scale: float,
    ) -> ProjectedPoint:
        """
        Wraps one local 2D point around a cylinder.
        """

        local_x = (
            point[0]
            * scale
        )

        local_y = (
            point[1]
            * scale
        )

        rotated_x, rotated_y = (
            GeometryProjectionEngine
            ._rotate_point_2d(
                x=local_x,
                y=local_y,
                rotation_degrees=(
                    rotation_degrees
                ),
            )
        )

        angular_offset = (
            rotated_x
            / radius
        )

        angle = (
            center_angle_radians
            + angular_offset
        )

        return ProjectedPoint(
            x=(
                origin[0]
                + radius
                * math.sin(
                    angle
                )
            ),
            y=(
                origin[1]
                + radius
                * math.cos(
                    angle
                )
            ),
            z=(
                center_z
                + rotated_y
            ),
        )

    @staticmethod
    def _cylinder_point_normal(
        point: ProjectedPoint,
        origin: Vector3,
    ) -> Vector3:
        """
        Calculates the outward radial normal at one
        cylindrical projected point.
        """

        radial_x = (
            point.x
            - origin[0]
        )

        radial_y = (
            point.y
            - origin[1]
        )

        length = math.sqrt(
            radial_x ** 2
            + radial_y ** 2
        )

        if length <= 0:
            raise ValueError(
                "Cannot calculate a cylinder normal "
                "at the cylinder axis."
            )

        return (
            radial_x / length,
            radial_y / length,
            0.0,
        )

    @staticmethod
    def _rotate_point_2d(
        x: float,
        y: float,
        rotation_degrees: float,
    ) -> tuple[float, float]:
        """
        Rotates one point around the local origin.
        """

        angle_radians = math.radians(
            rotation_degrees
        )

        cosine = math.cos(
            angle_radians
        )

        sine = math.sin(
            angle_radians
        )

        return (
            x * cosine
            - y * sine,
            x * sine
            + y * cosine,
        )

    @staticmethod
    def _normalize_vector(
        vector: Vector3,
    ) -> Vector3:
        """
        Returns a unit-length vector.
        """

        length = math.sqrt(
            vector[0] ** 2
            + vector[1] ** 2
            + vector[2] ** 2
        )

        if length <= 0:
            raise ValueError(
                "Cannot normalize a zero-length vector."
            )

        return (
            vector[0] / length,
            vector[1] / length,
            vector[2] / length,
        )

    @staticmethod
    def _read_positive_float(
        value: object,
        parameter_name: str,
    ) -> float:
        """
        Reads a positive numeric Surface parameter.
        """

        if isinstance(
            value,
            bool,
        ) or not isinstance(
            value,
            (
                int,
                float,
                str,
            ),
        ):
            raise ValueError(
                f"Surface {parameter_name} "
                "must be numeric."
            )

        try:
            result = float(
                value
            )

        except ValueError as error:
            raise ValueError(
                f"Surface {parameter_name} "
                "must be numeric."
            ) from error

        if result <= 0:
            raise ValueError(
                f"Surface {parameter_name} "
                "must be greater than zero."
            )

        return result

    @staticmethod
    def _read_vector3(
        value: object,
        parameter_name: str,
    ) -> Vector3:
        """
        Reads a three-dimensional numeric vector.
        """

        if not isinstance(
            value,
            (
                tuple,
                list,
            ),
        ):
            raise ValueError(
                f"Surface {parameter_name} "
                "must contain three values."
            )

        if len(
            value
        ) != 3:
            raise ValueError(
                f"Surface {parameter_name} "
                "must contain exactly three values."
            )

        raw_values = (
            value[0],
            value[1],
            value[2],
        )

        if not all(
            isinstance(
                item,
                (
                    int,
                    float,
                    str,
                ),
            )
            and not isinstance(
                item,
                bool,
            )
            for item in raw_values
        ):
            raise ValueError(
                f"Surface {parameter_name} "
                "values must be numeric."
            )

        try:
            return (
                float(
                    raw_values[0]
                ),
                float(
                    raw_values[1]
                ),
                float(
                    raw_values[2]
                ),
            )

        except ValueError as error:
            raise ValueError(
                f"Surface {parameter_name} "
                "values must be numeric."
            ) from error

    @staticmethod
    def _validate_uniform_xy_scale(
        placement: Placement,
    ) -> None:
        """
        Validates uniform local 2D scaling.
        """

        if (
            placement.scale[0]
            != placement.scale[1]
        ):
            raise NotImplementedError(
                "GeometryProjectionEngine currently "
                "supports uniform XY scaling only."
            )

    @staticmethod
    def _is_positive_z_normal(
        normal: Vector3,
        tolerance: float = 1e-9,
    ) -> bool:
        """
        Returns whether a normal points along +Z.
        """

        return (
            abs(
                normal[0]
            )
            <= tolerance
            and abs(
                normal[1]
            )
            <= tolerance
            and abs(
                normal[2]
                - 1.0
            )
            <= tolerance
        )