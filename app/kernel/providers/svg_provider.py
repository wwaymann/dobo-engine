"""
DOBO CAD Kernel

SVG Provider

Loads closed SVG paths and converts them into
surface-independent Contours.

The Provider performs only SVG parsing and 2D geometry
generation. Placement, extrusion and boolean operations
belong to their corresponding Kernel Engines.
"""

from __future__ import annotations

import os

import cadquery as cq
from svgpathtools import svg2paths2

from kernel.contracts.contour import Contour
from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest

from .provider import Provider

Point2D = tuple[float, float]


class SVGProvider(Provider):
    """
    Generates a ContourSet from closed SVG paths.

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
        return (
            "Loads closed SVG paths and converts " "them into two-dimensional contours."
        )

    def validate(
        self,
        request: ProviderRequest,
    ) -> None:
        """
        Validates SVG-specific parameters.
        """

        file_value = request.get_parameter("file")

        width_value = request.get_parameter("width")

        samples_value = request.get_parameter(
            "samples_per_path",
            128,
        )

        flip_y_value = request.get_parameter(
            "flip_y",
            True,
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

        if not isinstance(
            flip_y_value,
            bool,
        ):
            raise TypeError("SVG flip_y must be a boolean.")

    def build_contours(
        self,
        request: ProviderRequest,
    ) -> ContourSet:
        """
        Loads, samples, normalizes and converts
        SVG paths into a ContourSet.
        """

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

        raw_contours, skipped_open_paths = self._load_raw_contours(
            file_path=file_path,
            samples_per_path=samples_per_path,
            flip_y=flip_y,
        )

        normalized_contours, height = self._normalize_contours(
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
                "width": target_width,
                "height": height,
                "samples_per_path": (samples_per_path),
                "skipped_open_paths": (skipped_open_paths),
                "flip_y": flip_y,
            },
        )

    @staticmethod
    def _load_raw_contours(
        file_path: str,
        samples_per_path: int,
        flip_y: bool,
    ) -> tuple[
        list[list[Point2D]],
        int,
    ]:
        """
        Reads closed SVG paths and samples them
        as point collections.
        """

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

        return (
            raw_contours,
            skipped_open_paths,
        )

    @staticmethod
    def _normalize_contours(
        contours: list[list[Point2D]],
        target_width: float,
    ) -> tuple[
        list[list[Point2D]],
        float,
    ]:
        """
        Centers all contours around the origin and
        scales them uniformly to target_width.
        """

        all_x = [point[0] for contour in contours for point in contour]

        all_y = [point[1] for contour in contours for point in contour]

        minimum_x = min(all_x)

        maximum_x = max(all_x)

        minimum_y = min(all_y)

        maximum_y = max(all_y)

        source_width = maximum_x - minimum_x

        source_height = maximum_y - minimum_y

        if source_width <= 0:
            raise ValueError("SVG source width must be " "greater than zero.")

        center_x = (minimum_x + maximum_x) / 2.0

        center_y = (minimum_y + maximum_y) / 2.0

        scale_factor = target_width / source_width

        normalized_contours = [
            [
                (
                    (point[0] - center_x) * scale_factor,
                    (point[1] - center_y) * scale_factor,
                )
                for point in contour
            ]
            for contour in contours
        ]

        normalized_height = source_height * scale_factor

        return (
            normalized_contours,
            normalized_height,
        )

    @staticmethod
    def _build_wire(
        points: list[Point2D],
    ) -> cq.Wire:
        """
        Converts one sampled contour into
        a closed CadQuery Wire.
        """

        if len(points) < 3:
            raise ValueError("SVG contour requires at least " "three points.")

        workplane = cq.Workplane("XY").polyline(points).close()

        geometry = workplane.val()

        if not isinstance(
            geometry,
            cq.Wire,
        ):
            raise RuntimeError("SVGProvider could not create " "a closed Wire.")

        if not geometry.isValid():
            raise RuntimeError("SVGProvider created an invalid Wire.")

        return geometry

    @staticmethod
    def _resolve_file_path(
        file_value: str,
    ) -> str:
        """
        Resolves absolute paths and paths relative
        to the project root.
        """

        normalized_value = file_value.strip()

        if not normalized_value:
            raise ValueError("SVG file path cannot be empty.")

        if os.path.isabs(normalized_value):
            resolved_path = normalized_value

        else:
            project_root = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "..",
                )
            )

            resolved_path = os.path.join(
                project_root,
                normalized_value,
            )

        resolved_path = os.path.abspath(resolved_path)

        if not os.path.isfile(resolved_path):
            raise FileNotFoundError(f"SVG file not found: {resolved_path}")

        return resolved_path
