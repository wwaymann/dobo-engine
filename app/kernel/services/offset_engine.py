"""
DOBO CAD Kernel

Offset Engine

Transforms projected contours into inner and outer
offset layers using one local normal per point.

This service contains mathematical geometry only.
It must not import CadQuery or OpenCascade.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from kernel.contracts.offset_contour import (
    OffsetContour,
)
from kernel.contracts.offset_contour_set import (
    OffsetContourSet,
)
from kernel.contracts.offset_point import (
    OffsetPoint,
)
from kernel.contracts.projected_contour import (
    ProjectedContour,
)
from kernel.contracts.projected_contour_set import (
    ProjectedContourSet,
)
from kernel.contracts.projected_point import (
    ProjectedPoint,
)


Vector3 = tuple[float, float, float]


class OffsetEngineInterface(ABC):
    """
    Public interface for mathematical offset engines.
    """

    @abstractmethod
    def offset(
        self,
        contours: ProjectedContourSet,
        distance: float,
        symmetric: bool = True,
    ) -> OffsetContourSet:
        """
        Applies thickness along projected point normals.
        """


class OffsetEngine(
    OffsetEngineInterface,
):
    """
    Default mathematical Offset Engine.

    It creates one inner and one outer point for every
    projected point.

    Supported modes:

    - symmetric=True:
        inner = point - normal * distance / 2
        outer = point + normal * distance / 2

    - symmetric=False:
        inner = point
        outer = point + normal * distance
    """

    def offset(
        self,
        contours: ProjectedContourSet,
        distance: float,
        symmetric: bool = True,
    ) -> OffsetContourSet:
        """
        Converts ProjectedContourSet into OffsetContourSet.
        """

        contours.validate()

        normalized_distance = (
            self._read_positive_distance(
                distance
            )
        )

        if not isinstance(
            symmetric,
            bool,
        ):
            raise TypeError(
                "OffsetEngine symmetric must be boolean."
            )

        offset_contours = tuple(
            self._offset_contour(
                contour=contour,
                distance=normalized_distance,
                symmetric=symmetric,
            )
            for contour in contours.contours
        )

        result = OffsetContourSet(
            contours=offset_contours,
            source=contours,
            metadata={
                **contours.metadata,
                "engine": "offset",
                "distance": normalized_distance,
                "symmetric": symmetric,
                "contour_count": len(
                    offset_contours
                ),
            },
        )

        result.validate()

        return result

    def _offset_contour(
        self,
        contour: ProjectedContour,
        distance: float,
        symmetric: bool,
    ) -> OffsetContour:
        """
        Offsets one projected contour.
        """

        contour.validate()

        if not contour.has_normals:
            raise ValueError(
                "OffsetEngine requires one normal "
                "per projected point."
            )

        if len(
            contour.points
        ) != len(
            contour.normals
        ):
            raise ValueError(
                "OffsetEngine point and normal counts "
                "must match."
            )

        offset_points = tuple(
            self._offset_point(
                point=point,
                normal=normal,
                distance=distance,
                symmetric=symmetric,
            )
            for point, normal in zip(
                contour.points,
                contour.normals,
                strict=True,
            )
        )

        result = OffsetContour(
            points=offset_points,
            closed=contour.closed,
            metadata={
                **contour.metadata,
                "distance": distance,
                "symmetric": symmetric,
                "source_point_count": (
                    contour.count
                ),
            },
        )

        result.validate()

        return result

    def _offset_point(
        self,
        point: ProjectedPoint,
        normal: Vector3,
        distance: float,
        symmetric: bool,
    ) -> OffsetPoint:
        """
        Offsets one point along its normalized local normal.
        """

        point.validate()

        normalized_normal = (
            self._normalize_vector(
                normal
            )
        )

        if symmetric:
            inner_distance = (
                -distance
                / 2.0
            )

            outer_distance = (
                distance
                / 2.0
            )

        else:
            inner_distance = 0.0

            outer_distance = distance

        inner = self._translate_point(
            point=point,
            direction=normalized_normal,
            distance=inner_distance,
        )

        outer = self._translate_point(
            point=point,
            direction=normalized_normal,
            distance=outer_distance,
        )

        result = OffsetPoint(
            source=point,
            normal=normalized_normal,
            inner=inner,
            outer=outer,
            distance=distance,
        )

        result.validate()

        self._validate_offset_distance(
            source=point,
            inner=inner,
            outer=outer,
            distance=distance,
        )

        return result

    @staticmethod
    def _translate_point(
        point: ProjectedPoint,
        direction: Vector3,
        distance: float,
    ) -> ProjectedPoint:
        """
        Translates one projected point.
        """

        return ProjectedPoint(
            x=(
                point.x
                + direction[0]
                * distance
            ),
            y=(
                point.y
                + direction[1]
                * distance
            ),
            z=(
                point.z
                + direction[2]
                * distance
            ),
        )

    @staticmethod
    def _normalize_vector(
        vector: Vector3,
    ) -> Vector3:
        """
        Returns a normalized three-dimensional vector.
        """

        if not isinstance(
            vector,
            tuple,
        ) or len(
            vector
        ) != 3:
            raise ValueError(
                "OffsetEngine normal must contain "
                "three values."
            )

        for coordinate in vector:
            if isinstance(
                coordinate,
                bool,
            ) or not isinstance(
                coordinate,
                (
                    int,
                    float,
                ),
            ):
                raise TypeError(
                    "OffsetEngine normal coordinates "
                    "must be numeric."
                )

        length = math.sqrt(
            float(
                vector[0]
            )
            ** 2
            + float(
                vector[1]
            )
            ** 2
            + float(
                vector[2]
            )
            ** 2
        )

        if length <= 1e-12:
            raise ValueError(
                "OffsetEngine cannot use "
                "a zero-length normal."
            )

        return (
            float(
                vector[0]
            )
            / length,
            float(
                vector[1]
            )
            / length,
            float(
                vector[2]
            )
            / length,
        )

    @staticmethod
    def _read_positive_distance(
        value: object,
    ) -> float:
        """
        Reads a positive offset distance.
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
                "Offset distance must be numeric."
            )

        try:
            result = float(
                value
            )

        except ValueError as error:
            raise ValueError(
                "Offset distance must be numeric."
            ) from error

        if not math.isfinite(
            result
        ):
            raise ValueError(
                "Offset distance must be finite."
            )

        if result <= 0:
            raise ValueError(
                "Offset distance must be "
                "greater than zero."
            )

        return result

    @staticmethod
    def _distance_between_points(
        first: ProjectedPoint,
        second: ProjectedPoint,
    ) -> float:
        """
        Returns Euclidean distance between two points.
        """

        return math.sqrt(
            (
                second.x
                - first.x
            )
            ** 2
            + (
                second.y
                - first.y
            )
            ** 2
            + (
                second.z
                - first.z
            )
            ** 2
        )

    @classmethod
    def _validate_offset_distance(
        cls,
        source: ProjectedPoint,
        inner: ProjectedPoint,
        outer: ProjectedPoint,
        distance: float,
        tolerance: float = 1e-8,
    ) -> None:
        """
        Verifies that inner-to-outer thickness equals
        the requested distance.
        """

        del source

        actual_distance = (
            cls._distance_between_points(
                inner,
                outer,
            )
        )

        if not math.isclose(
            actual_distance,
            distance,
            rel_tol=tolerance,
            abs_tol=tolerance,
        ):
            raise RuntimeError(
                "OffsetEngine produced an incorrect "
                "inner-to-outer distance."
            )