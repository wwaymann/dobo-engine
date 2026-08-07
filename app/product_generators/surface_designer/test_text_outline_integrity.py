from __future__ import annotations

from product_generators.surface_features.occ_triangulation import (
    OCCPlanarTriangulator,
)
from product_generators.surface_features.topology import (
    SurfaceFeatureTopologyAnalyzer,
)

from .text_outlines import (
    TextOutlineExtractor,
)


def main() -> None:
    print()
    print("DOBO Text Outline Integrity - OCC")
    print("-----------------------------------")

    extractor = TextOutlineExtractor()
    triangulator = OCCPlanarTriangulator()

    for text in (
        "DOBO",
        "OPEN",
        "B8",
    ):
        document = extractor.extract(
            text,
            size=14.0,
            font="Arial",
            document_id=f"text_{text}",
        )

        topology = (
            SurfaceFeatureTopologyAnalyzer()
            .analyze(document)
        )

        triangle_total = 0

        for index, contour in enumerate(
            document.contours
        ):
            try:
                mesh = triangulator.triangulate(
                    contour
                )
            except Exception as error:
                raise RuntimeError(
                    f"{text}: OCC triangulation failed for "
                    f"contour {index} ({contour.id}); "
                    f"points={len(contour.points)}"
                ) from error

            triangle_total += len(
                mesh.triangles
            )

        print(
            text,
            "contours",
            len(document.contours),
            "holes",
            len(topology.holes),
            "triangles",
            triangle_total,
            "OCC OK",
        )

    print("-----------------------------------")
    print("Text outlines: Valid OCC OK")
    print()


if __name__ == "__main__":
    main()
