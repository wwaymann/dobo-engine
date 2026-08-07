from __future__ import annotations

import os

import cadquery as cq

from .face_selector import SurfaceFaceSelector
from .native_svg_face import NativeSvgFaceDecorator
from .native_text_face import NativeTextFaceDecorator


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_designer/"
    "phase_3_organic_diagnostic"
)

# Very simple asymmetric mark. It must remain recognizable if mapping is sane.
SVG_MARK = """
<svg xmlns="http://www.w3.org/2000/svg">
  <path d="M 0 0 L 36 0 L 36 8 L 14 8 L 14 28 L 6 28 L 6 8 L 0 8 Z"/>
</svg>
"""


def _export(shape: cq.Shape, filename: str) -> str:
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

    path = os.path.join(
        OUTPUT_DIRECTORY,
        filename,
    )

    cq.exporters.export(shape, path)

    if not os.path.isfile(path):
        raise RuntimeError(
            f"{filename}: export failed."
        )

    return path


def _smooth_organic() -> cq.Shape:
    """
    Smooth organic loft.

    Important difference from the original Phase 3 gallery:
    each section is ONE circular wire, not a 72-segment polygon.

    The changing radius plus lateral drift produces a genuinely curved
    freeform loft while keeping the lateral skin coherent enough for
    face-level UV mapping.
    """
    sections = (
        # z, radius, x_shift, y_shift
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
        for z, radius, x_shift, y_shift in sections
    )

    body = cq.Solid.makeLoft(
        wires,
        ruled=False,
    ).clean()

    if not body.isValid():
        raise RuntimeError(
            "Smooth organic diagnostic body is invalid."
        )

    return body


def _describe_body(
    body: cq.Shape,
) -> None:
    faces = tuple(body.Faces())

    print(
        "Organic body:",
        "faces",
        len(faces),
        "solids",
        len(body.Solids()),
        "valid",
        body.isValid(),
    )

    ordered = sorted(
        (
            (
                index,
                face.geomType(),
                float(face.Area()),
                face.uvBounds(),
            )
            for index, face in enumerate(faces)
        ),
        key=lambda item: item[2],
        reverse=True,
    )

    print("Largest faces:")

    for index, geom_type, area, bounds in ordered[:8]:
        print(
            " ",
            index,
            geom_type,
            "area",
            round(area, 3),
            "uv",
            tuple(
                round(float(value), 6)
                for value in bounds
            ),
        )


def _describe_result(
    label: str,
    result,
) -> None:
    mapped_box = result.mapped_faces.BoundingBox()
    tool_box = result.tool.BoundingBox()

    print(
        label,
        "mapped faces",
        len(result.mapped_faces.Faces()),
        "mapped bbox",
        (
            round(mapped_box.xlen, 3),
            round(mapped_box.ylen, 3),
            round(mapped_box.zlen, 3),
        ),
        "tool solids",
        len(result.tool.Solids()),
        "tool bbox",
        (
            round(tool_box.xlen, 3),
            round(tool_box.ylen, 3),
            round(tool_box.zlen, 3),
        ),
    )


def build_diagnostic():
    selector = SurfaceFaceSelector()
    text_decorator = NativeTextFaceDecorator()
    svg_decorator = NativeSvgFaceDecorator()

    body = _smooth_organic()

    _describe_body(body)

    target = selector.largest_external(body)

    print(
        "Selected target:",
        target.geomType(),
        "area",
        round(float(target.Area()), 3),
        "uv",
        tuple(
            round(float(value), 6)
            for value in target.uvBounds()
        ),
    )

    _export(
        body,
        "organic_clean_body.step",
    )

    # Large text deliberately uses a substantial portion of the face.
    text_result = text_decorator.decorate(
        base_shape=body,
        target_face=target,
        text_value="DOBO",
        size=12.0,
        mode="emboss",
        depth=2.0,
        font="Arial",
        kind="bold",
        width_fraction=0.52,
        height_fraction=0.30,
        u_center=0.50,
        v_center=0.52,
    )

    _describe_result(
        "TEXT",
        text_result,
    )

    _export(
        text_result.mapped_faces,
        "organic_text_mapped_faces.step",
    )
    _export(
        text_result.tool,
        "organic_text_tool.step",
    )
    _export(
        text_result.shape,
        "organic_text_emboss_large.step",
    )

    # Recreate untouched body for SVG.
    body_svg = _smooth_organic()
    target_svg = selector.largest_external(
        body_svg
    )

    svg_result = svg_decorator.decorate(
        base_shape=body_svg,
        target_face=target_svg,
        svg=SVG_MARK,
        mode="deboss",
        depth=2.0,
        width_fraction=0.42,
        height_fraction=0.32,
        u_center=0.50,
        v_center=0.48,
        document_id="organic_diagnostic_mark",
    )

    _describe_result(
        "SVG",
        svg_result,
    )

    _export(
        svg_result.mapped_faces,
        "organic_svg_mapped_faces.step",
    )
    _export(
        svg_result.tool,
        "organic_svg_tool.step",
    )
    _export(
        svg_result.shape,
        "organic_svg_deboss_large.step",
    )

    return (
        text_result,
        svg_result,
    )


if __name__ == "__main__":
    build_diagnostic()
