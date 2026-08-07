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
from product_generators.surface_mapping.document_mapper import (
    VectorSurfaceMapper,
)
from product_generators.surface_mapping.radial_mapper import (
    RadialProfileSurfaceMapper,
)
from product_generators.vector_geometry.svg_parser import (
    SvgVectorParser,
)

from .normal_extrusion import (
    SurfaceNormalExtruder,
)
from .normal_strip import (
    SurfaceNormalStripBuilder,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_features/phase_3_2"
)

SVG = """
<svg xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="28" height="20"/>
  <path d="M 36 0 L 48 10 L 36 20 L 24 10 Z"/>
</svg>
"""


def _export(
    shapes: list[cq.Shape],
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

    compound = cq.Compound.makeCompound(
        shapes
    )

    if not compound.isValid():
        raise RuntimeError(
            f"{filename}: invalid gallery geometry."
        )

    cq.exporters.export(
        compound,
        path,
    )

    if not os.path.isfile(
        path
    ):
        raise RuntimeError(
            f"{filename}: export failed."
        )

    return path


def _build(
    surface,
    filename: str,
) -> str:
    document = (
        SvgVectorParser()
        .parse_string(
            SVG,
            document_id=filename,
        )
    )

    contours = (
        VectorSurfaceMapper()
        .map_document(
            document,
            surface,
            v_offset=25.0,
        )
    )

    extruder = (
        SurfaceNormalExtruder()
    )

    strip_builder = (
        SurfaceNormalStripBuilder()
    )

    shapes: list[cq.Shape] = []

    for contour in contours:
        result = extruder.extrude_contour(
            contour,
            depth=4.0,
            radius=0.85,
        )

        shapes.append(
            result.shape
        )

        shapes.append(
            strip_builder.build(
                contour,
                depth=4.0,
            )
        )

    return _export(
        shapes,
        filename,
    )


def build_gallery() -> tuple[str, ...]:
    radius_function = (
        lambda z:
        50.0
        + 7.0
        * math.sin(
            z / 20.0
        )
    )

    derivative_function = (
        lambda z:
        (7.0 / 20.0)
        * math.cos(
            z / 20.0
        )
    )

    return (
        _build(
            CylinderSurfaceMapper(
                radius=50.0,
            ),
            "normal_extrusion_cylinder.step",
        ),
        _build(
            ConeSurfaceMapper(
                base_radius=56.0,
                top_radius=40.0,
                height=100.0,
            ),
            "normal_extrusion_cone.step",
        ),
        _build(
            RadialProfileSurfaceMapper(
                radius_function=(
                    radius_function
                ),
                derivative_function=(
                    derivative_function
                ),
            ),
            "normal_extrusion_radial.step",
        ),
    )
