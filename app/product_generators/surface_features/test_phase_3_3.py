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

from .closed_feature_solid import (
    ClosedSurfaceFeatureSolidBuilder,
)
from .gallery_phase_3_3 import (
    build_gallery,
)


def main() -> None:
    print()
    print(
        "DOBO Advanced Geometry - Phase 3.3"
    )
    print(
        "Closed Surface Feature Solid"
    )
    print(
        "-----------------------------------"
    )

    document = (
        SvgVectorParser()
        .parse_string(
            (
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<path d="M 0 0 L 24 0 L 30 10 '
                'L 24 20 L 0 20 L 6 10 Z"/>'
                "</svg>"
            ),
            document_id=(
                "closed_feature_test"
            ),
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
        ClosedSurfaceFeatureSolidBuilder()
        .build(
            contour,
            depth=3.0,
        )
    )

    result.validate()

    print(
        "Triangles:",
        result.triangle_count,
        "OK",
    )

    print(
        "Shape type:",
        type(
            result.shape
        ).__name__,
        "OK",
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
        "Phase 3.3: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
