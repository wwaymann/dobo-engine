"""
DOBO CAD Kernel

SVG Provider

Loads closed SVG paths and converts them into
surface-independent Contours.
"""

from __future__ import annotations

import os
from typing import Any

import cadquery as cq
from svgpathtools import svg2paths2

from kernel.contracts.contour import Contour
from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest

from .provider import Provider

Point2D = tuple[float, float]


class SVGProvider(Provider):
    """
    Generates Contours from closed SVG paths.

    Required parameters:

    - file
    - width

    Optional parameters:

    - samples_per_path
    - flip_y
    """

    @property
    def name(self) -> str:
        return "svg"

    @property
    def aliases(self) -> tuple[str, ...]:
        return (
            "vector",
            "logo",
        )

    @property
    def description(self) -> str:
        return "Loads closed SVG paths and converts " "them into Contours."

    def validate(
        self,
        request: ProviderRequest,
    ) -> None:
        file_value = request.get_parameter("file")

        width_value = request.get_parameter("width")

        samples_value = request.get_parameter(
            "samples_per_path",
            128,
        )

        if (
            not isinstance(
                file_value,
                str,
            )
            or not file_value.strip()
        ):
            raise ValueError("SVGProvider requires a non-empty " "'file' parameter.")

        file_path = self._resolve_file_path(file_value)

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"SVG file not found: {file_path}")

        if width_value is None:
            raise ValueError("SVGProvider requires 'width'.")

        try:
            width = float(width_value)

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError("SVG width must be numeric.") from error

        if width <= 0:
            raise ValueError("SVG width must be greater than zero.")

        try:
            samples_per_path = int(samples_value)

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError("SVG samples_per_path must be " "an integer.") from error

        if samples_per_path < 16:
            raise ValueError("SVG samples_per_path must be " "at least 16.")

    def build_contours(
        self,
        request: ProviderRequest,
    ) -> ContourSet:
        file_path = self._resolve_file_path(str(request.get_parameter("file")))

        target_width = float(request.get_parameter("width"))

        samples_per_path = int(
            request.get_parameter(
                "samples_per_path",
                128,
            )
        )

        flip_y = bool(
            request.get_parameter(
                "flip_y",
                True,
            )
        )

        svg_result = svg2paths2(file_path)

        paths = svg_result[0]

        raw_contours: list[list[Point2D]] = []

        skipped_open_paths = 0

        for path in paths:
            if not path.isclosed():
                skipped_open_paths += 1
                continue

            points: list[Point2D] = []

            for sample_index in range(samples_per_path):
                parameter = sample_index / samples_per_path

                point = path.point(parameter)

                x_value = float(point.real)

                y_value = float(point.imag)

                if flip_y:
                    y_value = -y_value

                points.append(
                    (
                        x_value,
                        y_value,
                    )
                )

            if len(points) >= 3:
                raw_contours.append(points)

        if not raw_contours:
            raise ValueError("The SVG does not contain usable " "closed paths.")

        normalized_contours = self._normalize_contours(
            contours=raw_contours,
            target_width=target_width,
        )

        contours: list[Contour] = []

        for contour_index, points in enumerate(normalized_contours):
            wire = self._build_wire(points)

            contours.append(
                Contour(
                    geometry=wire,
                    source=self.name,
                    metadata={
                        "contour_index": (contour_index),
                        "point_count": len(points),
                        "file": file_path,
                    },
                )
            )

        return ContourSet(
            contours=contours,
            source=self.name,
            metadata={
                "provider": self.name,
                "file": file_path,
                "target_width": target_width,
                "samples_per_path": (samples_per_path),
                "skipped_open_paths": (skipped_open_paths),
                "flip_y": flip_y,
            },
        )

    @staticmethod
    def _normalize_contours(
        contours: list[list[Point2D]],
        target_width: float,
    ) -> list[list[Point2D]]:
        """
        Centers all SVG contours around the origin
        and scales them uniformly.
        """

        all_x = [point[0] for contour in contours for point in contour]

        all_y = [point[1] for contour in contours for point in contour]

        minimum_x = min(all_x)

        maximum_x = max(all_x)

        minimum_y = min(all_y)

        maximum_y = max(all_y)

        source_width = maximum_x - minimum_x

        if source_width <= 0:
            raise ValueError("SVG source width must be " "greater than zero.")

        center_x = (minimum_x + maximum_x) / 2.0

        center_y = (minimum_y + maximum_y) / 2.0

        scale_factor = target_width / source_width

        return [
            [
                (
                    (point[0] - center_x) * scale_factor,
                    (point[1] - center_y) * scale_factor,
                )
                for point in contour
            ]
            for contour in contours
        ]

    @staticmethod
    def _build_wire(
        points: list[Point2D],
    ) -> cq.Wire:
        """
        Converts one normalized point list
        into a closed CadQuery Wire.
        """

        workplane = cq.Workplane("XY").polyline(points).close()

        geometry = workplane.val()

        if not isinstance(
            geometry,
            cq.Wire,
        ):
            raise RuntimeError("SVGProvider could not create " "a closed Wire.")

        return geometry

    @staticmethod
    def _resolve_file_path(
        file_value: str,
    ) -> str:
        """
        Resolves absolute paths and paths relative
        to the project root.
        """

        if os.path.isabs(file_value):
            return os.path.abspath(file_value)

        project_root = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
            )
        )

        return os.path.abspath(
            os.path.join(
                project_root,
                file_value,
            )
        )
