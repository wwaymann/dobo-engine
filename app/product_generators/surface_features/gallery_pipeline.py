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

from .pipeline import (
    SurfaceFeatureMode,
    SurfaceFeaturePipeline,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_features/pipeline"
)

FEATURE_SVG = """
<svg xmlns="http://www.w3.org/2000/svg">
  <path d="M 0 0 L 24 0 L 31 10 L 24 20 L 0 20 L 7 10 Z"/>
</svg>
"""

CYLINDER_RADIUS = 50.0
CYLINDER_HEIGHT = 100.0

CONE_BASE_RADIUS = 58.0
CONE_TOP_RADIUS = 42.0
CONE_HEIGHT = 110.0

RADIAL_HEIGHT = 110.0

OVERLAP = 0.6
FEATURE_DEPTH = 3.0


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

    section_count = 12
    point_count = 64

    for section in range(
        section_count
    ):
        z = (
            RADIAL_HEIGHT
            * section
            / (section_count - 1)
        )

        radius = _radial_radius(
            z
        )

        points = tuple(
            cq.Vector(
                radius
                * math.cos(
                    2.0
                    * math.pi
                    * index
                    / point_count
                ),
                radius
                * math.sin(
                    2.0
                    * math.pi
                    * index
                    / point_count
                ),
                z,
            )
            for index in range(
                point_count
            )
        )

        wires.append(
            cq.Wire.makePolygon(
                points,
                close=True,
            )
        )

    body = cq.Solid.makeLoft(
        wires,
        ruled=False,
    )

    if not body.isValid():
        raise RuntimeError(
            "Radial gallery body is invalid."
        )

    return body.clean()


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


def _cylinder_case(
    mode: SurfaceFeatureMode,
):
    body = cq.Solid.makeCylinder(
        CYLINDER_RADIUS,
        CYLINDER_HEIGHT,
    ).clean()

    mapped_radius = (
        CYLINDER_RADIUS - OVERLAP
        if mode is SurfaceFeatureMode.EMBOSS
        else CYLINDER_RADIUS + OVERLAP
    )

    mapper = CylinderSurfaceMapper(
        radius=mapped_radius,
    )

    return (
        body,
        mapper,
        FEATURE_DEPTH + OVERLAP,
        35.0,
    )


def _cone_case(
    mode: SurfaceFeatureMode,
):
    body = cq.Solid.makeCone(
        CONE_BASE_RADIUS,
        CONE_TOP_RADIUS,
        CONE_HEIGHT,
    ).clean()

    shift = (
        -OVERLAP
        if mode is SurfaceFeatureMode.EMBOSS
        else OVERLAP
    )

    mapper = ConeSurfaceMapper(
        base_radius=(
            CONE_BASE_RADIUS
            + shift
        ),
        top_radius=(
            CONE_TOP_RADIUS
            + shift
        ),
        height=CONE_HEIGHT,
    )

    return (
        body,
        mapper,
        FEATURE_DEPTH + OVERLAP,
        40.0,
    )


def _radial_case(
    mode: SurfaceFeatureMode,
):
    body = _radial_body()

    shift = (
        -OVERLAP
        if mode is SurfaceFeatureMode.EMBOSS
        else OVERLAP
    )

    mapper = RadialProfileSurfaceMapper(
        radius_function=(
            lambda z:
            _radial_radius(z)
            + shift
        ),
        derivative_function=(
            _radial_derivative
        ),
    )

    return (
        body,
        mapper,
        FEATURE_DEPTH + OVERLAP,
        40.0,
    )


def build_gallery():
    pipeline = SurfaceFeaturePipeline()

    cases = (
        (
            "emboss_cylinder.step",
            SurfaceFeatureMode.EMBOSS,
            _cylinder_case,
        ),
        (
            "deboss_cylinder.step",
            SurfaceFeatureMode.DEBOSS,
            _cylinder_case,
        ),
        (
            "emboss_cone.step",
            SurfaceFeatureMode.EMBOSS,
            _cone_case,
        ),
        (
            "deboss_cone.step",
            SurfaceFeatureMode.DEBOSS,
            _cone_case,
        ),
        (
            "emboss_radial.step",
            SurfaceFeatureMode.EMBOSS,
            _radial_case,
        ),
        (
            "deboss_radial.step",
            SurfaceFeatureMode.DEBOSS,
            _radial_case,
        ),
    )

    outputs = []

    for filename, mode, factory in cases:
        (
            body,
            mapper,
            depth,
            v_offset,
        ) = factory(mode)

        result = pipeline.apply_svg(
            svg=FEATURE_SVG,
            document_id=(
                filename.replace(
                    ".step",
                    ""
                )
            ),
            surface=mapper,
            base_shape=body,
            mode=mode,
            depth=depth,
            u_offset=0.0,
            v_offset=v_offset,
        )

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

    return tuple(outputs)
