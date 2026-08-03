"""
DOBO CAD Kernel

Surface Contract

Defines the target surface on which geometry
will be positioned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SurfaceType(str, Enum):
    """
    Surface types supported by the Kernel.
    """

    PLANE = "plane"
    CYLINDER = "cylinder"
    CONE = "cone"
    SPHERE = "sphere"
    MESH = "mesh"
    NURBS = "nurbs"
    BEZIER = "bezier"


@dataclass(frozen=True, slots=True)
class Surface:
    """
    Describes a target geometric surface.

    Surface contains only the information required
    to calculate placement.

    It does not contain source Contours or solids.
    """

    type: SurfaceType

    parameters: dict[str, Any] = field(default_factory=dict)

    identifier: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validates the surface definition.
        """

        if self.type == SurfaceType.PLANE:
            self._validate_plane()

        elif self.type == SurfaceType.CYLINDER:
            self._validate_cylinder()

        elif self.type == SurfaceType.CONE:
            self._validate_cone()

        elif self.type == SurfaceType.SPHERE:
            self._validate_sphere()

        elif self.type in {
            SurfaceType.MESH,
            SurfaceType.NURBS,
            SurfaceType.BEZIER,
        }:
            self._validate_external_geometry()

        else:
            raise ValueError(f"Unsupported surface type: {self.type}")

    def _validate_plane(self) -> None:
        """
        Validates a planar surface.
        """

        normal = self.parameters.get(
            "normal",
            (0.0, 0.0, 1.0),
        )

        if not isinstance(normal, tuple):
            raise ValueError("Plane normal must be a tuple.")

        if len(normal) != 3:
            raise ValueError("Plane normal must contain " "three values.")

        if all(float(value) == 0.0 for value in normal):
            raise ValueError("Plane normal cannot be a zero vector.")

    def _validate_cylinder(self) -> None:
        """
        Validates a cylindrical surface.
        """

        radius = float(
            self.parameters.get(
                "radius",
                0,
            )
        )

        height = float(
            self.parameters.get(
                "height",
                0,
            )
        )

        if radius <= 0:
            raise ValueError("Cylinder radius must be greater than 0.")

        if height <= 0:
            raise ValueError("Cylinder height must be greater than 0.")

    def _validate_cone(self) -> None:
        """
        Validates a conical or truncated-cone surface.
        """

        bottom_radius = float(
            self.parameters.get(
                "bottom_radius",
                0,
            )
        )

        top_radius = float(
            self.parameters.get(
                "top_radius",
                0,
            )
        )

        height = float(
            self.parameters.get(
                "height",
                0,
            )
        )

        if bottom_radius < 0:
            raise ValueError("Cone bottom_radius cannot be negative.")

        if top_radius < 0:
            raise ValueError("Cone top_radius cannot be negative.")

        if bottom_radius == 0 and top_radius == 0:
            raise ValueError("Cone must have at least one " "positive radius.")

        if height <= 0:
            raise ValueError("Cone height must be greater than 0.")

    def _validate_sphere(self) -> None:
        """
        Validates a spherical surface.
        """

        radius = float(
            self.parameters.get(
                "radius",
                0,
            )
        )

        if radius <= 0:
            raise ValueError("Sphere radius must be greater than 0.")

    def _validate_external_geometry(self) -> None:
        """
        Validates surfaces represented by external
        or backend-specific geometry.
        """

        geometry = self.parameters.get("geometry")

        if geometry is None:
            raise ValueError(
                f"{self.type.value} surface requires " "a geometry parameter."
            )
