from __future__ import annotations

import os

from product_generators.surface_mapping.cylinder_mapper import (
    CylinderSurfaceMapper,
)
from product_generators.surface_mapping.document_mapper import (
    VectorSurfaceMapper,
)
from product_generators.vector_geometry.svg_parser import (
    SvgVectorParser,
)

from .gallery_phase_3_2 import (
    build_gallery,
)
from .normal_extrusion import (
    SurfaceNormalExtruder,
)
from .normal_strip import (
    SurfaceNormalStripBuilder,
)


def main() -> None:
    print()
    print(
        "DOBO Advanced Geometry - Phase 3.2"
    )
    print(
        "Normal Extrusion"
    )
    print(
        "-----------------------------------"
    )

    document = (
        SvgVectorParser()
        .parse_string(
            (
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect x="0" y="0" width="20" height="14"/>'
                "</svg>"
            ),
            document_id="normal_test",
        )
    )

    contour = (
        VectorSurfaceMapper()
        .map_document(
            document,
            CylinderSurfaceMapper(
                radius=50.0
            ),
            v_offset=30.0,
        )[0]
    )

    result = (
        SurfaceNormalExtruder()
        .extrude_contour(
            contour,
            depth=3.0,
            radius=0.7,
        )
    )

    result.validate()

    print(
        "Normal samples:",
        result.sample_count,
        "OK",
    )

    strip = (
        SurfaceNormalStripBuilder()
        .build(
            contour,
            depth=3.0,
        )
    )

    if not strip.isValid():
        raise RuntimeError(
            "Normal strip is invalid."
        )

    print(
        "Normal side strip: OK"
    )

    for path in build_gallery():
        size = os.path.getsize(
            path
        )

        if size <= 0:
            raise RuntimeError(
                f"{path}: empty STEP."
            )

        print(
            os.path.basename(path),
            size,
            "bytes",
            "OK",
        )

    print(
        "-----------------------------------"
    )
    print(
        "Phase 3.2: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
