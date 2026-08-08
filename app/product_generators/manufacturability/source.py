from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

from product_generators.surface_designer.composition_spec import (
    ProductCompositionParser,
)
from product_generators.surface_designer.gallery_phase_4_hybrid import (
    _boolean_details,
    _hybridize,
    _organic_core,
    _primary_solid,
)


@dataclass(frozen=True, slots=True)
class StructuralBodySource:
    structural_body: cq.Shape
    internal_cavity: cq.Shape | None = None
    drainage_tools: tuple[cq.Shape, ...] = ()
    declared_closed_cavities: tuple[cq.Shape, ...] = ()
    source_label: str = "structural_body"

    def validate(self) -> None:
        if not self.structural_body.isValid():
            raise RuntimeError("Structural body source is invalid.")

        if len(self.structural_body.Solids()) != 1:
            raise RuntimeError(
                "Structural body source must contain exactly one solid."
            )

        if self.internal_cavity is not None:
            if not self.internal_cavity.isValid():
                raise RuntimeError(
                    "Explicit internal cavity source is invalid."
                )

            if len(self.internal_cavity.Solids()) < 1:
                raise RuntimeError(
                    "Explicit internal cavity contains no solid."
                )

            if float(self.internal_cavity.Volume()) <= 0.0:
                raise RuntimeError(
                    "Explicit internal cavity has zero volume."
                )

        for index, tool in enumerate(self.drainage_tools, start=1):
            if (
                not tool.isValid()
                or float(tool.Volume()) <= 0.0
            ):
                raise RuntimeError(
                    f"Drainage tool {index} is invalid."
                )

        for index, cavity in enumerate(
            self.declared_closed_cavities,
            start=1,
        ):
            if (
                not cavity.isValid()
                or float(cavity.Volume()) <= 0.0
            ):
                raise RuntimeError(
                    f"Declared closed cavity {index} is invalid."
                )


def build_structural_body_source(
    specification_path: str | Path,
) -> StructuralBodySource:
    spec = ProductCompositionParser().parse_file(
        specification_path
    )

    body = _organic_core()

    if spec.primitives:
        body = _hybridize(body)

    if spec.booleans:
        body = _boolean_details(body)

    body = _primary_solid(body)

    result = StructuralBodySource(
        structural_body=body,
        source_label="phase4_hybrid_structural_body",
    )

    result.validate()
    return result


def make_planter_semantic_fixture(
    *,
    outer_radius: float = 30.0,
    height: float = 50.0,
    wall: float = 2.0,
    bottom: float = 2.0,
    drainage_radius: float = 2.0,
) -> StructuralBodySource:
    if outer_radius <= 0.0:
        raise ValueError("outer_radius must be positive.")

    if height <= 0.0:
        raise ValueError("height must be positive.")

    if wall <= 0.0:
        raise ValueError("wall must be positive.")

    if bottom <= 0.0:
        raise ValueError("bottom must be positive.")

    if drainage_radius <= 0.0:
        raise ValueError("drainage_radius must be positive.")

    if bottom >= height:
        raise ValueError("bottom must be smaller than height.")

    inner_radius = outer_radius - wall

    if inner_radius <= 0.0:
        raise ValueError("wall is too large for fixture radius.")

    outer: cq.Shape = (
        cq.Workplane("XY")
        .circle(outer_radius)
        .extrude(height)
        .findSolid()
    )

    cavity_tool: cq.Shape = (
        cq.Workplane("XY")
        .workplane(offset=bottom)
        .circle(inner_radius)
        .extrude(height - bottom + 1.0)
        .findSolid()
    )

    body: cq.Shape = (
        outer
        .cut(cavity_tool)
        .clean()
    )

    drainage: cq.Shape = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .circle(drainage_radius)
        .extrude(bottom + 2.0)
        .findSolid()
    )

    usable_cavity: cq.Shape = (
        cq.Workplane("XY")
        .workplane(offset=bottom)
        .circle(inner_radius)
        .extrude(height - bottom)
        .findSolid()
    )

    result = StructuralBodySource(
        structural_body=body,
        internal_cavity=usable_cavity,
        drainage_tools=(drainage,),
        declared_closed_cavities=(),
        source_label="planter_semantic_fixture",
    )

    result.validate()
    return result