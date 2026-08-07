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

from .surface_feature_api import (
    SurfaceFeatureAPI,
    SurfaceFeatureMode,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_features/phase_3_4"
)

OVERLAP = 0.7
DEPTH = 3.2

NESTED_SVG = """
<svg xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="34" height="26"/>
  <rect x="7" y="6" width="20" height="14"/>
  <rect x="13" y="10" width="8" height="6"/>
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

    if not os.path.isfile(path):
        raise RuntimeError(
            f"{filename}: STEP export failed."
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
    sections = 12
    points_per_section = 64
    height = 110.0

    for section in range(sections):
        z = (
            height
            * section
            / (sections - 1)
        )

        radius = _radial_radius(z)

        points = tuple(
            cq.Vector(
                radius
                * math.cos(
                    2.0
                    * math.pi
                    * index
                    / points_per_section
                ),
                radius
                * math.sin(
                    2.0
                    * math.pi
                    * index
                    / points_per_section
                ),
                z,
            )
            for index in range(
                points_per_section
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


def _case(
    kind: str,
    mode: SurfaceFeatureMode,
):
    if kind == "cylinder":
        radius = 50.0

        body = cq.Solid.makeCylinder(
            radius,
            105.0,
        ).clean()

        mapped_radius = (
            radius - OVERLAP
            if mode is SurfaceFeatureMode.EMBOSS
            else radius + OVERLAP
        )

        mapper = CylinderSurfaceMapper(
            radius=mapped_radius,
        )

        return body, mapper, 35.0

    if kind == "cone":
        base = 58.0
        top = 42.0
        height = 110.0

        body = cq.Solid.makeCone(
            base,
            top,
            height,
        ).clean()

        shift = (
            -OVERLAP
            if mode is SurfaceFeatureMode.EMBOSS
            else OVERLAP
        )

        mapper = ConeSurfaceMapper(
            base_radius=base + shift,
            top_radius=top + shift,
            height=height,
        )

        return body, mapper, 40.0

    if kind == "radial":
        body = _radial_body()

        shift = (
            -OVERLAP
            if mode is SurfaceFeatureMode.EMBOSS
            else OVERLAP
        )

        mapper = (
            RadialProfileSurfaceMapper(
                radius_function=(
                    lambda z:
                    _radial_radius(z)
                    + shift
                ),
                derivative_function=(
                    _radial_derivative
                ),
            )
        )

        return body, mapper, 40.0

    raise ValueError(
        f"Unsupported gallery kind '{kind}'."
    )


def build_gallery():
    api = SurfaceFeatureAPI()

    outputs = []

    for kind in (
        "cylinder",
        "cone",
        "radial",
    ):
        for mode in (
            SurfaceFeatureMode.EMBOSS,
            SurfaceFeatureMode.DEBOSS,
        ):
            body, mapper, v_offset = (
                _case(
                    kind,
                    mode,
                )
            )

            filename = (
                f"{mode.value}_nested_{kind}.step"
            )

            result = api.apply_svg(
                svg=NESTED_SVG,
                base_shape=body,
                surface=mapper,
                mode=mode,
                depth=DEPTH + OVERLAP,
                document_id=(
                    filename.replace(
                        ".step",
                        ""
                    )
                ),
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
