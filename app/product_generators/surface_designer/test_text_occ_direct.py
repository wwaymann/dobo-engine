from __future__ import annotations

import cadquery as cq

from product_generators.surface_mapping.cylinder_mapper import (
    CylinderSurfaceMapper,
)

from .text_surface_feature import (
    DirectOCCTextSurfaceFeatureBuilder,
    TextSurfaceMode,
)


def main() -> None:
    print()
    print("DOBO Direct OCC Text Surface Test")
    print("-----------------------------------")

    builder = DirectOCCTextSurfaceFeatureBuilder()

    for text in ("DOBO", "OPEN", "B8"):
        base = cq.Solid.makeCylinder(
            50.0,
            110.0,
        ).clean()

        surface = CylinderSurfaceMapper(
            radius=49.3,
        )

        result = builder.apply(
            base_shape=base,
            surface=surface,
            text=text,
            size=12.0,
            depth=3.8,
            mode=TextSurfaceMode.EMBOSS,
            font="Arial",
            v_offset=45.0,
        )

        result.validate()

        solids = tuple(result.shape.Solids())

        if len(solids) != 1:
            raise RuntimeError(
                f"{text}: expected one final body."
            )

        print(
            text,
            "glyph-faces",
            result.glyph_face_count,
            "triangles",
            result.triangle_count,
            "booleans",
            result.boolean_count,
            "fragments",
            result.discarded_fragment_count,
            "solids",
            len(solids),
            "OK",
        )

    print("-----------------------------------")
    print("Direct OCC text: Valid OK")
    print()


if __name__ == "__main__":
    main()
