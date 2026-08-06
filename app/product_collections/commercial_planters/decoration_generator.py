from __future__ import annotations

import math

from kernel.contracts.contour_definition import ContourDefinition
from kernel.contracts.geometry_definition import GeometryDefinition

from .specification import CommercialPlanterSpecification


class CommercialDecorationGenerator:
    """
    Generates planar decoration profiles.

    Profiles are defined in the global X/Z dimensions but initially
    lie in the Kernel XY sketch plane. The product runner later rotates
    them onto the planter's front face.
    """

    def generate(
        self,
        specification: CommercialPlanterSpecification,
    ) -> tuple[GeometryDefinition, ...]:
        specification.validate()

        profiles = self._profiles(
            specification
        )

        definitions: list[GeometryDefinition] = []

        for index, points in enumerate(profiles):
            contour = ContourDefinition(
                id=(
                    f"{specification.id}:"
                    f"decoration-contour:{index}"
                ),
                points=points,
                closed=True,
                source="commercial_planters",
                metadata={
                    "decoration": specification.decoration,
                    "mode": specification.mode,
                    "index": index,
                },
            )
            contour.validate()

            definition = GeometryDefinition(
                id=(
                    f"{specification.id}:"
                    f"decoration-definition:{index}"
                ),
                outer_contour=contour,
                source="commercial_planters",
                metadata={
                    "decoration": specification.decoration,
                    "mode": specification.mode,
                    "index": index,
                },
            )
            definition.validate()
            definitions.append(definition)

        return tuple(definitions)

    def _profiles(
        self,
        specification: CommercialPlanterSpecification,
    ) -> tuple[tuple[tuple[float, float], ...], ...]:
        cx = float(specification.width) / 2.0
        cz = float(specification.decoration_center_z)
        w = float(specification.decoration_width)
        h = float(specification.decoration_height)

        if specification.decoration == "plate":
            return (
                self._rectangle(cx, cz, w, h),
            )

        if specification.decoration == "circle":
            radius = min(w, h) / 2.0
            return (
                self._circle(cx, cz, radius),
            )

        if specification.decoration == "diamond":
            return (
                (
                    (cx, cz - h / 2.0),
                    (cx + w / 2.0, cz),
                    (cx, cz + h / 2.0),
                    (cx - w / 2.0, cz),
                ),
            )

        if specification.decoration == "frame":
            bar = min(5.0, h / 5.0)
            return (
                self._rectangle(
                    cx,
                    cz - h / 2.0 + bar / 2.0,
                    w,
                    bar,
                ),
                self._rectangle(
                    cx,
                    cz + h / 2.0 - bar / 2.0,
                    w,
                    bar,
                ),
                self._rectangle(
                    cx - w / 2.0 + bar / 2.0,
                    cz,
                    bar,
                    h - 2.0 * bar,
                ),
                self._rectangle(
                    cx + w / 2.0 - bar / 2.0,
                    cz,
                    bar,
                    h - 2.0 * bar,
                ),
            )

        if specification.decoration == "brand_mark":
            bar = min(7.0, w / 7.0)
            gap = bar * 1.25
            return (
                self._rectangle(
                    cx - gap,
                    cz,
                    bar,
                    h,
                ),
                self._rectangle(
                    cx,
                    cz,
                    bar,
                    h * 0.72,
                ),
                self._rectangle(
                    cx + gap,
                    cz,
                    bar,
                    h,
                ),
            )

        raise ValueError(
            f"Unsupported decoration '{specification.decoration}'."
        )

    @staticmethod
    def _rectangle(
        cx: float,
        cy: float,
        width: float,
        height: float,
    ) -> tuple[tuple[float, float], ...]:
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

    @staticmethod
    def _circle(
        cx: float,
        cy: float,
        radius: float,
        *,
        samples: int = 64,
    ) -> tuple[tuple[float, float], ...]:
        return tuple(
            (
                cx
                + radius
                * math.cos(
                    2.0 * math.pi * index / samples
                ),
                cy
                + radius
                * math.sin(
                    2.0 * math.pi * index / samples
                ),
            )
            for index in range(samples)
        )
