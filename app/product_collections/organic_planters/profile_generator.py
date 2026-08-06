from __future__ import annotations

import math

from kernel.contracts.contour_definition import ContourDefinition
from kernel.contracts.geometry_definition import GeometryDefinition

from .specification import OrganicPlanterSpecification


class OrganicProfileGenerator:
    """
    Generates outer and inner loft sections for organic planters.

    Organic planters intentionally use solid loft + inner loft CUT
    instead of OCC shell/hollow, which is less reliable on complex
    loft topology.
    """

    def generate_outer_sections(
        self,
        specification: OrganicPlanterSpecification,
    ) -> tuple[
        tuple[GeometryDefinition, ...],
        tuple[tuple[float, float, float], ...],
    ]:
        specification.validate()

        return self._generate_sections(
            specification,
            inner=False,
        )

    def generate_inner_sections(
        self,
        specification: OrganicPlanterSpecification,
    ) -> tuple[
        tuple[GeometryDefinition, ...],
        tuple[tuple[float, float, float], ...],
    ]:
        specification.validate()

        return self._generate_sections(
            specification,
            inner=True,
        )

    def _generate_sections(
        self,
        specification: OrganicPlanterSpecification,
        *,
        inner: bool,
    ) -> tuple[
        tuple[GeometryDefinition, ...],
        tuple[tuple[float, float, float], ...],
    ]:
        definitions: list[GeometryDefinition] = []
        offsets: list[tuple[float, float, float]] = []

        wall = float(
            specification.wall_thickness
        )

        bottom_z = (
            wall
            if inner
            else 0.0
        )

        top_z = (
            float(specification.height) + 1.0
            if inner
            else float(specification.height)
        )

        usable_height = (
            top_z - bottom_z
        )

        for index, section in enumerate(
            specification.sections
        ):
            z_ratio, sx, sy, ox, oy = section

            outer_width = (
                float(specification.width)
                * float(sx)
            )

            outer_depth = (
                float(specification.depth)
                * float(sy)
            )

            if inner:
                section_width = (
                    outer_width
                    - 2.0 * wall
                )
                section_depth = (
                    outer_depth
                    - 2.0 * wall
                )

                if (
                    section_width <= 0.0
                    or section_depth <= 0.0
                ):
                    raise ValueError(
                        "Organic planter wall thickness "
                        "is too large for an inner section."
                    )
            else:
                section_width = outer_width
                section_depth = outer_depth

            points = self._profile_points(
                profile=specification.profile,
                width=section_width,
                depth=section_depth,
            )

            role = (
                "inner"
                if inner
                else "outer"
            )

            contour = ContourDefinition(
                id=(
                    f"{specification.id}:"
                    f"{role}-section-contour:{index}"
                ),
                points=points,
                closed=True,
                source="organic_planters",
                metadata={
                    "role": role,
                    "section_index": index,
                    "z_ratio": float(z_ratio),
                    "scale_x": float(sx),
                    "scale_y": float(sy),
                },
            )
            contour.validate()

            definition = GeometryDefinition(
                id=(
                    f"{specification.id}:"
                    f"{role}-section-definition:{index}"
                ),
                outer_contour=contour,
                source="organic_planters",
                metadata={
                    "role": role,
                    "section_index": index,
                },
            )
            definition.validate()
            definitions.append(definition)

            z = (
                bottom_z
                + usable_height * float(z_ratio)
            )

            offsets.append(
                (
                    float(specification.width)
                    * float(ox),
                    float(specification.depth)
                    * float(oy),
                    z,
                )
            )

        return (
            tuple(definitions),
            tuple(offsets),
        )

    def _profile_points(
        self,
        *,
        profile: str,
        width: float,
        depth: float,
    ) -> tuple[tuple[float, float], ...]:
        if profile == "circle":
            diameter = min(
                float(width),
                float(depth),
            )
            radius = diameter / 2.0

            return self._ellipse(
                radius,
                radius,
                samples=96,
            )

        if profile == "ellipse":
            return self._ellipse(
                float(width) / 2.0,
                float(depth) / 2.0,
                samples=96,
            )

        if profile == "rounded_square":
            return self._superellipse(
                float(width) / 2.0,
                float(depth) / 2.0,
                exponent=4.0,
                samples=96,
            )

        raise ValueError(
            f"Unsupported organic profile '{profile}'."
        )

    @staticmethod
    def _ellipse(
        rx: float,
        ry: float,
        *,
        samples: int,
    ) -> tuple[tuple[float, float], ...]:
        return tuple(
            (
                rx * math.cos(
                    2.0 * math.pi * index / samples
                ),
                ry * math.sin(
                    2.0 * math.pi * index / samples
                ),
            )
            for index in range(samples)
        )

    @staticmethod
    def _superellipse(
        rx: float,
        ry: float,
        *,
        exponent: float,
        samples: int,
    ) -> tuple[tuple[float, float], ...]:
        points: list[tuple[float, float]] = []

        power = 2.0 / exponent

        for index in range(samples):
            angle = (
                2.0 * math.pi * index / samples
            )

            cosine = math.cos(angle)
            sine = math.sin(angle)

            x = (
                rx
                * math.copysign(
                    abs(cosine) ** power,
                    cosine,
                )
            )

            y = (
                ry
                * math.copysign(
                    abs(sine) ** power,
                    sine,
                )
            )

            points.append(
                (
                    float(x),
                    float(y),
                )
            )

        return tuple(points)
