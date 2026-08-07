from __future__ import annotations

import math
import os

import cadquery as cq

from product_generators.surface_mapping.cone_mapper import (
    ConeSurfaceMapper,
)
from product_generators.surface_mapping.cylinder_mapper import (
    CylinderSurfaceMapper,
)
from product_generators.surface_mapping.radial_mapper import (
    RadialProfileSurfaceMapper,
)

from .contracts import (
    SurfaceDesignMode,
)
from .designer import (
    SurfaceDesigner,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_designer/phase_2"
)

OVERLAP = 0.7
DEPTH = 3.8


def _export(
    shape: cq.Shape,
    filename: str,
) -> str:
    os.makedirs(
        OUTPUT_DIRECTORY,
        exist_ok=True,
    )

    path = os.path.join(
        OUTPUT_DIRECTORY,
        filename,
    )

    cq.exporters.export(
        shape,
        path,
    )

    if not os.path.isfile(
        path
    ):
        raise RuntimeError(
            f"{filename}: export failed."
        )

    return path


def _radial_radius(
    z: float,
) -> float:
    return (
        50.0
        + 7.0
        * math.sin(
            float(z) / 22.0
        )
    )


def _radial_derivative(
    z: float,
) -> float:
    return (
        (7.0 / 22.0)
        * math.cos(
            float(z) / 22.0
        )
    )


def _radial_body() -> cq.Shape:
    wires = []

    height = 110.0
    sections = 12
    samples = 64

    for section in range(
        sections
    ):
        z = (
            height
            * section
            / (sections - 1)
        )

        radius = (
            _radial_radius(
                z
            )
        )

        points = tuple(
            cq.Vector(
                radius
                * math.cos(
                    2.0
                    * math.pi
                    * index
                    / samples
                ),
                radius
                * math.sin(
                    2.0
                    * math.pi
                    * index
                    / samples
                ),
                z,
            )
            for index in range(
                samples
            )
        )

        wires.append(
            cq.Wire.makePolygon(
                points,
                close=True,
            )
        )

    return (
        cq.Solid.makeLoft(
            wires,
            ruled=False,
        )
        .clean()
    )


def build_gallery():
    designer = SurfaceDesigner()

    cylinder_radius = 50.0

    cylinder = (
        cq.Solid.makeCylinder(
            cylinder_radius,
            110.0,
        )
        .clean()
    )

    cylinder_surface = (
        CylinderSurfaceMapper(
            radius=(
                cylinder_radius
                - OVERLAP
            )
        )
    )

    cone_base = 58.0
    cone_top = 42.0
    cone_height = 110.0

    cone = (
        cq.Solid.makeCone(
            cone_base,
            cone_top,
            cone_height,
        )
        .clean()
    )

    cone_surface = (
        ConeSurfaceMapper(
            base_radius=(
                cone_base
                + OVERLAP
            ),
            top_radius=(
                cone_top
                + OVERLAP
            ),
            height=(
                cone_height
            ),
        )
    )

    radial = _radial_body()

    radial_surface = (
        RadialProfileSurfaceMapper(
            radius_function=(
                lambda z:
                _radial_radius(
                    z
                )
                - OVERLAP
            ),
            derivative_function=(
                _radial_derivative
            ),
        )
    )

    cases = (
        (
            "real_text_dobo_cylinder_emboss.step",
            lambda:
            designer.add_text(
                base_shape=cylinder,
                surface=cylinder_surface,
                text="DOBO",
                size=12.0,
                mode=SurfaceDesignMode.EMBOSS,
                depth=DEPTH,
                font="Arial",
                v_offset=45.0,
            ),
        ),
        (
            "real_text_open_cone_deboss.step",
            lambda:
            designer.add_text(
                base_shape=cone,
                surface=cone_surface,
                text="OPEN",
                size=11.0,
                mode=SurfaceDesignMode.DEBOSS,
                depth=DEPTH,
                font="Arial",
                v_offset=45.0,
            ),
        ),
        (
            "real_text_bold_radial_emboss.step",
            lambda:
            designer.add_text(
                base_shape=radial,
                surface=radial_surface,
                text="B8",
                size=14.0,
                mode=SurfaceDesignMode.EMBOSS,
                depth=DEPTH,
                font="Arial",
                kind="bold",
                v_offset=45.0,
            ),
        ),
    )

    outputs = []

    for filename, factory in cases:
        result = factory()
        result.validate()

        path = _export(
            result.shape,
            filename,
        )

        outputs.append(
            (
                path,
                result,
            )
        )

    return tuple(
        outputs
    )
