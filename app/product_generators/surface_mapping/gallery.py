from __future__ import annotations

import math
import os

import cadquery as cq

from product_generators.vector_geometry.svg_parser import (
    SvgVectorParser,
)

from .cone_mapper import (
    ConeSurfaceMapper,
)
from .cylinder_mapper import (
    CylinderSurfaceMapper,
)
from .document_mapper import (
    VectorSurfaceMapper,
)
from .radial_mapper import (
    RadialProfileSurfaceMapper,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_mapping"
)

PATH_RADIUS = 0.8

SVG = """
<svg xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="24" height="18"/>
  <path d="M 30 0 L 42 9 L 30 18 L 18 9 Z"/>
</svg>
"""


def _vector(
    point: tuple[float, float, float],
) -> cq.Vector:
    return cq.Vector(
        float(point[0]),
        float(point[1]),
        float(point[2]),
    )


def _segment_solid(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    *,
    radius: float,
) -> cq.Shape:
    start_vector = _vector(start)
    end_vector = _vector(end)

    direction = (
        end_vector - start_vector
    )

    length = direction.Length

    if length <= 1e-9:
        return cq.Solid.makeSphere(
            radius,
            start_vector,
        )

    return cq.Solid.makeCylinder(
        radius,
        length,
        start_vector,
        direction,
    )


def _mapped_contour_solid(
    samples,
    *,
    closed: bool,
    radius: float = PATH_RADIUS,
) -> cq.Shape:
    """
    Converts a mapped 3D contour into visible geometry.

    STEP viewers often hide wire-only geometry. This function
    creates a thin round solid along every mapped segment.
    """

    points = [
        sample.point
        for sample in samples
    ]

    if len(points) < 2:
        raise ValueError(
            "Mapped contour requires at least two points."
        )

    shapes: list[cq.Shape] = []

    pair_count = (
        len(points)
        if closed
        else len(points) - 1
    )

    for index in range(pair_count):
        start = points[index]

        end = points[
            (index + 1) % len(points)
        ]

        shapes.append(
            _segment_solid(
                start,
                end,
                radius=radius,
            )
        )

    for point in points:
        shapes.append(
            cq.Solid.makeSphere(
                radius,
                _vector(point),
            )
        )

    return cq.Compound.makeCompound(
        shapes
    )


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

    compound = (
        cq.Compound.makeCompound(
            shapes
        )
    )

    if not compound.isValid():
        raise RuntimeError(
            f"{filename}: gallery compound is invalid."
        )

    cq.exporters.export(
        compound,
        path,
    )

    if not os.path.isfile(
        path
    ):
        raise RuntimeError(
            f"Failed to export {filename}."
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

    mapped = (
        VectorSurfaceMapper()
        .map_document(
            document,
            surface,
            v_offset=20.0,
        )
    )

    shapes = [
        _mapped_contour_solid(
            contour.samples,
            closed=contour.closed,
        )
        for contour in mapped
    ]

    return _export(
        shapes,
        filename,
    )


def build_gallery() -> tuple[str, ...]:
    radius_function = (
        lambda z:
        50.0
        + 8.0
        * math.sin(
            z / 18.0
        )
    )

    derivative_function = (
        lambda z:
        (8.0 / 18.0)
        * math.cos(
            z / 18.0
        )
    )

    return (
        _build(
            CylinderSurfaceMapper(
                radius=50.0
            ),
            "mapped_cylinder.step",
        ),
        _build(
            ConeSurfaceMapper(
                base_radius=55.0,
                top_radius=40.0,
                height=100.0,
            ),
            "mapped_cone.step",
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
            "mapped_free_radial.step",
        ),
    )
