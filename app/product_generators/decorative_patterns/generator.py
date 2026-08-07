from __future__ import annotations

import math

from kernel.contracts.contour_definition import ContourDefinition
from kernel.contracts.geometry_definition import GeometryDefinition

from .specification import PatternSpecification


class DecorativePatternGenerator:
    """
    Produces reusable planar pattern elements.

    The generator knows nothing about planters or products.
    It only emits GeometryDefinition objects that downstream
    product collections can extrude, move, rotate and combine.
    """

    def generate(
        self,
        specification: PatternSpecification,
    ) -> tuple[GeometryDefinition, ...]:
        specification.validate()

        profiles = self._profiles(
            specification
        )

        definitions: list[GeometryDefinition] = []

        for index, points in enumerate(profiles):
            contour = ContourDefinition(
                id=f"{specification.id}:contour:{index}",
                points=points,
                closed=True,
                source="decorative_patterns",
                metadata={
                    "pattern": specification.pattern,
                    "index": index,
                },
            )
            contour.validate()

            definition = GeometryDefinition(
                id=f"{specification.id}:definition:{index}",
                outer_contour=contour,
                source="decorative_patterns",
                metadata={
                    "pattern": specification.pattern,
                    "index": index,
                },
            )
            definition.validate()
            definitions.append(definition)

        return tuple(definitions)

    def _profiles(
        self,
        specification: PatternSpecification,
    ) -> tuple[tuple[tuple[float, float], ...], ...]:
        if specification.pattern == "grid":
            return self._grid(specification)

        if specification.pattern == "brick":
            return self._brick(specification)

        if specification.pattern == "diamond":
            return self._diamond(specification)

        if specification.pattern == "chevron":
            return self._chevron(specification)

        if specification.pattern == "hex":
            return self._hex(specification)

        if specification.pattern == "wave_band":
            return self._wave_band(specification)

        raise ValueError(
            f"Unsupported pattern '{specification.pattern}'."
        )

    def _grid(
        self,
        s: PatternSpecification,
    ):
        profiles = []

        for row in range(s.rows):
            for col in range(s.columns):
                cx = (
                    s.element_width / 2.0
                    + col * (s.element_width + s.spacing_x)
                )
                cy = (
                    s.element_height / 2.0
                    + row * (s.element_height + s.spacing_y)
                )

                profiles.append(
                    self._rectangle(
                        cx,
                        cy,
                        s.element_width,
                        s.element_height,
                    )
                )

        return tuple(profiles)

    def _brick(
        self,
        s: PatternSpecification,
    ):
        profiles = []

        for row in range(s.rows):
            offset = (
                (s.element_width + s.spacing_x) / 2.0
                if row % 2
                else 0.0
            )

            for col in range(s.columns):
                cx = (
                    s.element_width / 2.0
                    + col * (s.element_width + s.spacing_x)
                    + offset
                )
                cy = (
                    s.element_height / 2.0
                    + row * (s.element_height + s.spacing_y)
                )

                profiles.append(
                    self._rectangle(
                        cx,
                        cy,
                        s.element_width,
                        s.element_height,
                    )
                )

        return tuple(profiles)

    def _diamond(
        self,
        s: PatternSpecification,
    ):
        profiles = []

        for row in range(s.rows):
            for col in range(s.columns):
                cx = (
                    s.element_width / 2.0
                    + col * (s.element_width + s.spacing_x)
                )
                cy = (
                    s.element_height / 2.0
                    + row * (s.element_height + s.spacing_y)
                )

                profiles.append(
                    (
                        (cx, cy - s.element_height / 2.0),
                        (cx + s.element_width / 2.0, cy),
                        (cx, cy + s.element_height / 2.0),
                        (cx - s.element_width / 2.0, cy),
                    )
                )

        return tuple(profiles)

    def _chevron(
        self,
        s: PatternSpecification,
    ):
        profiles = []

        bar = max(
            1.0,
            min(
                s.element_width,
                s.element_height,
            ) * 0.22,
        )

        for row in range(s.rows):
            for col in range(s.columns):
                cx = (
                    s.element_width / 2.0
                    + col * (s.element_width + s.spacing_x)
                )
                cy = (
                    s.element_height / 2.0
                    + row * (s.element_height + s.spacing_y)
                )

                profiles.append(
                    (
                        (cx - s.element_width / 2.0, cy - bar / 2.0),
                        (cx, cy + s.element_height / 2.0),
                        (cx + s.element_width / 2.0, cy - bar / 2.0),
                        (cx + s.element_width / 2.0 - bar, cy - bar / 2.0),
                        (cx, cy + s.element_height / 2.0 - bar),
                        (cx - s.element_width / 2.0 + bar, cy - bar / 2.0),
                    )
                )

        return tuple(profiles)

    def _hex(
        self,
        s: PatternSpecification,
    ):
        profiles = []

        rx = s.element_width / 2.0
        ry = s.element_height / 2.0

        for row in range(s.rows):
            row_offset = (
                (s.element_width + s.spacing_x) / 2.0
                if row % 2
                else 0.0
            )

            for col in range(s.columns):
                cx = (
                    rx
                    + col * (s.element_width + s.spacing_x)
                    + row_offset
                )
                cy = (
                    ry
                    + row * (s.element_height * 0.75 + s.spacing_y)
                )

                points = tuple(
                    (
                        cx + rx * math.cos(math.radians(60 * i)),
                        cy + ry * math.sin(math.radians(60 * i)),
                    )
                    for i in range(6)
                )

                profiles.append(points)

        return tuple(profiles)

    def _wave_band(
        self,
        s: PatternSpecification,
    ):
        profiles = []

        segments = max(8, s.columns * 4)
        amplitude = s.element_height / 2.0
        thickness = max(1.0, s.element_height * 0.25)

        for row in range(s.rows):
            baseline = (
                amplitude
                + row * (s.element_height + s.spacing_y)
            )

            upper = []
            lower = []

            for i in range(segments + 1):
                x = (
                    s.width * i / segments
                )
                y = (
                    baseline
                    + amplitude
                    * 0.55
                    * math.sin(
                        2.0
                        * math.pi
                        * s.columns
                        * x
                        / s.width
                    )
                )
                upper.append((x, y + thickness / 2.0))
                lower.append((x, y - thickness / 2.0))

            profiles.append(
                tuple(
                    upper
                    + list(reversed(lower))
                )
            )

        return tuple(profiles)

    @staticmethod
    def _rectangle(
        cx: float,
        cy: float,
        width: float,
        height: float,
    ):
        return (
            (
                cx - width / 2.0,
                cy - height / 2.0,
            ),
            (
                cx + width / 2.0,
                cy - height / 2.0,
            ),
            (
                cx + width / 2.0,
                cy + height / 2.0,
            ),
            (
                cx - width / 2.0,
                cy + height / 2.0,
            ),
        )
