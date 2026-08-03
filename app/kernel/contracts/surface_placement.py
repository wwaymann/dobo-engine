"""
DOBO CAD Kernel

SurfacePlacement Contract

Represents the result of adapting a ContourSet
to a target Surface.

SurfacePlacement connects surface-independent
2D geometry with the Extrusion Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .contour_set import ContourSet
from .placement import Placement
from .surface import Surface

Vector3 = tuple[float, float, float]
Matrix4 = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]


@dataclass(frozen=True, slots=True)
class LocalCoordinateSystem:
    """
    Represents a local orthonormal coordinate system
    calculated on the target Surface.
    """

    origin: Vector3

    x_axis: Vector3

    y_axis: Vector3

    normal: Vector3

    def validate(self) -> None:
        """
        Validates that the coordinate-system vectors
        are non-zero three-dimensional vectors.
        """

        vectors = (
            self.origin,
            self.x_axis,
            self.y_axis,
            self.normal,
        )

        for vector in vectors:
            if len(vector) != 3:
                raise ValueError(
                    "Local coordinate-system vectors " "must contain three values."
                )

        for name, vector in (
            ("x_axis", self.x_axis),
            ("y_axis", self.y_axis),
            ("normal", self.normal),
        ):
            if all(float(value) == 0.0 for value in vector):
                raise ValueError(
                    f"Local coordinate-system {name} " "cannot be a zero vector."
                )


@dataclass(frozen=True, slots=True)
class SurfaceSample:
    """
    Represents one calculated sample on a Surface.

    Segmented or projected placement strategies may
    produce multiple samples for the same geometry.
    """

    position: Vector3

    normal: Vector3

    tangent: Vector3

    vertical: Vector3

    source_parameter: float | None = None

    surface_coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    ) = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validates the sample vectors.
        """

        for name, vector in (
            ("position", self.position),
            ("normal", self.normal),
            ("tangent", self.tangent),
            ("vertical", self.vertical),
        ):
            if len(vector) != 3:
                raise ValueError(f"Surface sample {name} must " "contain three values.")

        for name, vector in (
            ("normal", self.normal),
            ("tangent", self.tangent),
            ("vertical", self.vertical),
        ):
            if all(float(value) == 0.0 for value in vector):
                raise ValueError(f"Surface sample {name} " "cannot be a zero vector.")


@dataclass(frozen=True, slots=True)
class PlacementQuality:
    """
    Describes the requested or achieved quality
    of the surface-adaptation operation.
    """

    strategy: str = "rigid"

    subdivision_count: int = 0

    sampling_resolution: int = 0

    linear_tolerance: float = 0.01

    angular_tolerance_degrees: float = 0.1

    projection_tolerance: float = 0.01

    def validate(self) -> None:
        """
        Validates quality parameters.
        """

        if self.strategy not in {
            "rigid",
            "segmented",
            "projected",
            "conformal",
        }:
            raise ValueError("Unsupported SurfacePlacement strategy.")

        if self.subdivision_count < 0:
            raise ValueError("Subdivision count cannot be negative.")

        if self.sampling_resolution < 0:
            raise ValueError("Sampling resolution cannot be negative.")

        if self.linear_tolerance <= 0:
            raise ValueError("Linear tolerance must be greater than 0.")

        if self.angular_tolerance_degrees <= 0:
            raise ValueError("Angular tolerance must be greater than 0.")

        if self.projection_tolerance <= 0:
            raise ValueError("Projection tolerance must be greater than 0.")


@dataclass(frozen=True, slots=True)
class SurfacePlacement:
    """
    Represents geometry fully adapted to a target
    Surface, but not yet converted into a solid.

    The original ContourSet remains unchanged.
    """

    id: str = field(default_factory=lambda: str(uuid4()))

    source_contours: ContourSet = field(default_factory=ContourSet)

    placed_contours: ContourSet = field(default_factory=ContourSet)

    surface: Surface | None = None

    placement: Placement = field(default_factory=Placement)

    local_coordinate_systems: tuple[
        LocalCoordinateSystem,
        ...,
    ] = ()

    surface_samples: tuple[
        SurfaceSample,
        ...,
    ] = ()

    transformations: tuple[
        Matrix4,
        ...,
    ] = ()

    quality: PlacementQuality = field(default_factory=PlacementQuality)

    projection_metadata: dict[str, Any] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validates the complete SurfacePlacement.
        """

        if self.surface is None:
            raise ValueError("SurfacePlacement requires a Surface.")

        if self.source_contours.is_empty:
            raise ValueError("SurfacePlacement requires source Contours.")

        if self.placed_contours.is_empty:
            raise ValueError("SurfacePlacement requires placed Contours.")

        if not self.source_contours.validate():
            raise ValueError("SurfacePlacement contains invalid " "source Contours.")

        if not self.placed_contours.validate():
            raise ValueError("SurfacePlacement contains invalid " "placed Contours.")

        self.surface.validate()
        self.placement.validate()
        self.quality.validate()

        for coordinate_system in self.local_coordinate_systems:
            coordinate_system.validate()

        for sample in self.surface_samples:
            sample.validate()

        for transformation in self.transformations:
            self._validate_matrix(transformation)

        if self.quality.strategy == "rigid" and not self.local_coordinate_systems:
            raise ValueError(
                "Rigid SurfacePlacement requires at least "
                "one local coordinate system."
            )

        if (
            self.quality.strategy
            in {
                "segmented",
                "projected",
                "conformal",
            }
            and not self.surface_samples
        ):
            raise ValueError(
                f"{self.quality.strategy.capitalize()} "
                "SurfacePlacement requires surface samples."
            )

    @property
    def is_segmented(self) -> bool:
        """
        Indicates whether geometry was adapted
        through multiple surface samples.
        """

        return self.quality.strategy in {
            "segmented",
            "projected",
            "conformal",
        }

    @property
    def sample_count(self) -> int:
        """
        Number of calculated surface samples.
        """

        return len(self.surface_samples)

    @staticmethod
    def _validate_matrix(
        matrix: Matrix4,
    ) -> None:
        """
        Validates a four-by-four transformation matrix.
        """

        if len(matrix) != 4:
            raise ValueError("Transformation matrix must " "contain four rows.")

        for row in matrix:
            if len(row) != 4:
                raise ValueError(
                    "Every transformation-matrix row " "must contain four values."
                )
