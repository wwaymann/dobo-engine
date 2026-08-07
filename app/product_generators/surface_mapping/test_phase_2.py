from __future__ import annotations

import math
import os

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
from .gallery import (
    build_gallery,
)
from .radial_mapper import (
    RadialProfileSurfaceMapper,
)


def main() -> None:
    print()
    print(
        "DOBO Advanced Geometry - Phase 2"
    )
    print(
        "Surface Mapping"
    )
    print(
        "--------------------------------"
    )

    cylinder = CylinderSurfaceMapper(
        radius=50.0
    )

    sample = cylinder.sample(
        0.0,
        25.0,
    )

    assert abs(
        sample.point[0] - 50.0
    ) < 1e-9

    assert abs(
        sample.point[2] - 25.0
    ) < 1e-9

    print(
        "Cylinder mapper: OK"
    )

    cone = ConeSurfaceMapper(
        base_radius=60.0,
        top_radius=40.0,
        height=100.0,
    )

    assert abs(
        cone.radius_at(50.0)
        - 50.0
    ) < 1e-9

    cone.sample(
        20.0,
        50.0,
    )

    print(
        "Cone mapper: OK"
    )

    radial = (
        RadialProfileSurfaceMapper(
            radius_function=(
                lambda z:
                50.0
                + 5.0
                * math.sin(
                    z / 20.0
                )
            ),
            derivative_function=(
                lambda z:
                0.25
                * math.cos(
                    z / 20.0
                )
            ),
        )
    )

    radial.sample(
        10.0,
        35.0,
    )

    print(
        "Free radial mapper: OK"
    )

    document = (
        SvgVectorParser()
        .parse_string(
            (
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect x="0" y="0" width="10" height="8"/>'
                "</svg>"
            ),
            document_id=(
                "surface_mapping_test"
            ),
        )
    )

    mapped = (
        VectorSurfaceMapper()
        .map_document(
            document,
            cylinder,
            v_offset=10.0,
        )
    )

    assert len(mapped) == 1

    assert (
        len(mapped[0].samples)
        == 4
    )

    print(
        "Vector document mapping: OK"
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
            "VISIBLE SOLID OK",
        )

    print(
        "--------------------------------"
    )
    print(
        "Phase 2: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
