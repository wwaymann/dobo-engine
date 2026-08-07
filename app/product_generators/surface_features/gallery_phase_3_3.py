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

from .closed_feature_solid import (
    ClosedSurfaceFeatureSolidBuilder,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_features/phase_3_3"
)

SVG = """
<svg xmlns="http://www.w3.org/2000/svg">
  <path d="M 0 0 L 30 0 L 38 12 L 30 24 L 0 24 L 8 12 Z"/>
</svg>
"""


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

    contour = (
        VectorSurfaceMapper()
        .map_document(
            document,
            surface,
            v_offset=30.0,
        )[0]
    )

    result = (
        ClosedSurfaceFeatureSolidBuilder()
        .build(
            contour,
            depth=4.0,
        )
    )

    result.validate()

    return _export(
        result.shape,
        filename,
    )


def build_gallery() -> tuple[str, ...]:
    radius_function = (
        lambda z:
        50.0
        + 8.0
        * math.sin(
            z / 20.0
        )
    )

    derivative_function = (
        lambda z:
        (8.0 / 20.0)
        * math.cos(
            z / 20.0
        )
    )

    return (
        _build(
            CylinderSurfaceMapper(
                radius=50.0,
            ),
            "closed_feature_cylinder.step",
        ),
        _build(
            ConeSurfaceMapper(
                base_radius=58.0,
                top_radius=40.0,
                height=110.0,
            ),
            "closed_feature_cone.step",
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
            "closed_feature_radial.step",
        ),
    )
