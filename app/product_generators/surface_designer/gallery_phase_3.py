from __future__ import annotations

import math
import os

import cadquery as cq

from cadquery.func import torus

from .face_selector import (
    SurfaceFaceSelector,
)
from .native_svg_face import (
    NativeSvgFaceDecorator,
)
from .native_text_face import (
    NativeTextFaceDecorator,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_designer/phase_3"
)

SVG = """
<svg xmlns="http://www.w3.org/2000/svg">
  <path d="M 0 0 L 22 0 L 30 10 L 22 20 L 0 20 L 8 10 Z"/>
  <rect x="9" y="6" width="8" height="8"/>
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
            f"{filename}: export failed."
        )

    return path


def _cone() -> cq.Shape:
    return cq.Solid.makeCone(
        55.0,
        35.0,
        100.0,
    ).clean()


def _sphere() -> cq.Shape:
    return cq.Solid.makeSphere(
        48.0
    ).clean()


def _torus() -> cq.Shape:
    result = torus(
        48.0,
        14.0,
    )

    if not result.isValid():
        raise RuntimeError(
            "Torus gallery body is invalid."
        )

    return result.clean()


def _organic() -> cq.Shape:
    sections = (
        (0.0, 42.0, 0.0),
        (18.0, 50.0, 2.0),
        (38.0, 44.0, -3.0),
        (60.0, 55.0, 3.0),
        (82.0, 47.0, -2.0),
        (105.0, 51.0, 0.0),
    )

    wires = []

    sample_count = 72

    for z, radius, x_shift in sections:
        points = tuple(
            cq.Vector(
                x_shift
                + radius
                * math.cos(
                    2.0 * math.pi * index / sample_count
                ),
                radius
                * math.sin(
                    2.0 * math.pi * index / sample_count
                ),
                z,
            )
            for index in range(
                sample_count
            )
        )

        wires.append(
            cq.Wire.makePolygon(
                points,
                close=True,
            )
        )

    shape = cq.Solid.makeLoft(
        wires,
        ruled=False,
    ).clean()

    if not shape.isValid():
        raise RuntimeError(
            "Organic gallery body is invalid."
        )

    return shape


def build_gallery():
    selector = SurfaceFaceSelector()
    text_decorator = NativeTextFaceDecorator()
    svg_decorator = NativeSvgFaceDecorator()

    outputs = []

    bodies = (
        (
            "cone",
            _cone,
            "CONE",
        ),
        (
            "sphere",
            _sphere,
            "SPHERE",
        ),
        (
            "torus",
            _torus,
            "TORUS",
        ),
        (
            "organic",
            _organic,
            None,
        ),
    )

    for name, factory, geom_type in bodies:
        # Text
        body = factory()

        target = selector.largest_external(
            body,
            geom_type=geom_type,
        )

        text_result = text_decorator.decorate(
            base_shape=body,
            target_face=target,
            text_value="DOBO",
            size=10.0,
            mode="emboss",
            depth=1.2,
            font="Arial",
            kind="bold",
            width_fraction=0.28,
            height_fraction=0.18,
            u_center=0.5,
            v_center=0.52,
        )

        text_path = _export(
            text_result.shape,
            f"text_{name}.step",
        )

        outputs.append(
            (
                text_path,
                text_result,
            )
        )

        # SVG
        body = factory()

        target = selector.largest_external(
            body,
            geom_type=geom_type,
        )

        svg_result = svg_decorator.decorate(
            base_shape=body,
            target_face=target,
            svg=SVG,
            mode="deboss",
            depth=1.0,
            width_fraction=0.24,
            height_fraction=0.20,
            u_center=0.5,
            v_center=0.48,
            document_id=f"svg_{name}",
        )

        svg_path = _export(
            svg_result.shape,
            f"svg_{name}.step",
        )

        outputs.append(
            (
                svg_path,
                svg_result,
            )
        )

    return tuple(outputs)
