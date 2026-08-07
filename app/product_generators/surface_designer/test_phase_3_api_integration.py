from __future__ import annotations

import os

import cadquery as cq

from .contracts import (
    SurfaceDesignMode,
)
from .designer import (
    SurfaceDesigner,
)
from .face_selector import (
    SurfaceFaceSelector,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/"
    "surface_designer/phase_3_api"
)

SVG = """
<svg xmlns="http://www.w3.org/2000/svg">
  <path d="M 0 0 L 34 0 L 34 8 L 14 8 L 14 28 L 6 28 L 6 8 L 0 8 Z"/>
</svg>
"""


def _organic() -> cq.Shape:
    sections = (
        (0.0,   42.0,  0.0,  0.0),
        (18.0,  49.0,  3.0, -1.0),
        (38.0,  44.0, -2.0,  2.0),
        (60.0,  55.0,  4.0,  0.0),
        (82.0,  47.0, -3.0, -2.0),
        (105.0, 51.0,  1.0,  1.0),
    )

    wires = tuple(
        cq.Wire.makeCircle(
            radius,
            cq.Vector(
                x_shift,
                y_shift,
                z,
            ),
            cq.Vector(
                0.0,
                0.0,
                1.0,
            ),
        )
        for z, radius, x_shift, y_shift
        in sections
    )

    body = cq.Solid.makeLoft(
        wires,
        ruled=False,
    ).clean()

    if not body.isValid():
        raise RuntimeError(
            "Organic API test body is invalid."
        )

    return body


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

    return path


def main() -> None:
    print()
    print(
        "DOBO Surface Designer - Phase 3 API"
    )
    print(
        "Universal SurfaceDesigner Integration"
    )
    print(
        "-----------------------------------"
    )

    designer = SurfaceDesigner()
    selector = SurfaceFaceSelector()

    # Public API: TEXT on organic target_face
    body = _organic()
    face = selector.largest_external(
        body
    )

    text_result = designer.add_text(
        base_shape=body,
        target_face=face,
        text="DOBO",
        size=12.0,
        mode=SurfaceDesignMode.EMBOSS,
        depth=2.0,
        font="Arial",
        kind="bold",
        width_fraction=0.52,
        height_fraction=0.30,
        u_center=0.50,
        v_center=0.52,
    )

    text_result.validate()

    if (
        text_result.metadata.get(
            "text_route"
        )
        != "cadquery_native_faceOn"
    ):
        raise RuntimeError(
            "add_text did not use universal target_face route."
        )

    if len(text_result.shape.Solids()) != 1:
        raise RuntimeError(
            "add_text must return one product solid."
        )

    text_path = _export(
        text_result.shape,
        "api_organic_text.step",
    )

    print(
        "add_text(target_face)",
        "solids",
        len(text_result.shape.Solids()),
        os.path.getsize(text_path),
        "bytes",
        "OK",
    )

    # Public API: SVG on organic target_face
    body = _organic()
    face = selector.largest_external(
        body
    )

    svg_result = designer.add_svg(
        base_shape=body,
        target_face=face,
        svg=SVG,
        mode=SurfaceDesignMode.DEBOSS,
        depth=2.0,
        width_fraction=0.42,
        height_fraction=0.32,
        u_center=0.50,
        v_center=0.48,
        document_id="phase_3_api_svg",
    )

    svg_result.validate()

    if (
        svg_result.metadata.get(
            "surface_route"
        )
        != "cadquery_native_faceOn"
    ):
        raise RuntimeError(
            "add_svg did not use universal target_face route."
        )

    if len(svg_result.shape.Solids()) != 1:
        raise RuntimeError(
            "add_svg must return one product solid."
        )

    svg_path = _export(
        svg_result.shape,
        "api_organic_svg.step",
    )

    print(
        "add_svg(target_face)",
        "solids",
        len(svg_result.shape.Solids()),
        os.path.getsize(svg_path),
        "bytes",
        "OK",
    )

    print(
        "-----------------------------------"
    )
    print(
        "Models: 2"
    )
    print(
        "Phase 3 API Integration: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
