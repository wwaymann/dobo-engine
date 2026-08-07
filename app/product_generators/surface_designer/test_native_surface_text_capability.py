from __future__ import annotations

import math
import os

import cadquery as cq


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_designer/native_text_probe"
)


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


def main() -> None:
    print()
    print(
        "DOBO Native Surface Text Capability"
    )
    print(
        "-----------------------------------"
    )

    try:
        from cadquery.func import (
            cylinder,
            offset,
            plane,
            text,
        )
    except Exception as error:
        raise RuntimeError(
            "Installed CadQuery does not expose the "
            "required free-function surface text API."
        ) from error

    print(
        "cadquery.func imports: OK"
    )

    diameter = 50.0
    height = 100.0
    font_size = 8.0
    thickness = 1.2

    base = (
        cylinder(
            diameter,
            height,
        )
        .moved(
            rz=-135
        )
    )

    lateral_face = (
        base.faces(
            "%CYLINDER"
        )
    )

    print(
        "Cylinder surface:",
        lateral_face.ShapeType(),
        "OK",
    )

    spine = (
        (
            base
            * plane()
            .moved(
                z=height / 2.0
            )
        )
        .edges()
        .trim(
            math.pi / 2.0,
            math.pi,
        )
    )

    print(
        "Spine:",
        spine.ShapeType(),
        "OK",
    )

    projected = text(
        "DOBO",
        font_size,
        spine,
        lateral_face,
        font="Arial",
        kind="regular",
        halign="center",
        valign="center",
    )

    if not projected.isValid():
        raise RuntimeError(
            "Native projected text is invalid."
        )

    print(
        "Projected text:",
        projected.ShapeType(),
        "faces",
        len(
            projected.Faces()
        ),
        "OK",
    )

    projected_path = _export(
        projected,
        "native_text_projected.step",
    )

    thickened = offset(
        projected,
        thickness,
        cap=True,
    )

    if not thickened.isValid():
        raise RuntimeError(
            "Native thickened surface text is invalid."
        )

    print(
        "Thickened text:",
        thickened.ShapeType(),
        "solids",
        len(
            thickened.Solids()
        ),
        "volume",
        round(
            float(
                thickened.Volume()
            ),
            6,
        ),
        "OK",
    )

    thickened_path = _export(
        thickened,
        "native_text_thickened.step",
    )

    print(
        os.path.basename(
            projected_path
        ),
        os.path.getsize(
            projected_path
        ),
        "bytes",
        "OK",
    )

    print(
        os.path.basename(
            thickened_path
        ),
        os.path.getsize(
            thickened_path
        ),
        "bytes",
        "OK",
    )

    print(
        "-----------------------------------"
    )
    print(
        "Native surface text capability: VALID OK"
    )
    print()


if __name__ == "__main__":
    main()
