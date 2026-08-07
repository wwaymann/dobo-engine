from __future__ import annotations

from .gallery_phase_3_organic_diagnostic import (
    build_diagnostic,
)


def main() -> None:
    print()
    print(
        "DOBO Surface Designer - Phase 3"
    )
    print(
        "Organic Surface Diagnostic"
    )
    print(
        "-----------------------------------"
    )

    text_result, svg_result = (
        build_diagnostic()
    )

    for name, result in (
        ("organic_text", text_result),
        ("organic_svg", svg_result),
    ):
        result.validate()

        solids = tuple(
            result.shape.Solids()
        )

        if len(solids) != 1:
            raise RuntimeError(
                f"{name}: final result must contain one solid."
            )

        delta = (
            result.final_volume
            - result.base_volume
            if result.mode == "emboss"
            else result.base_volume
            - result.final_volume
        )

        if delta <= 0.0:
            raise RuntimeError(
                f"{name}: no positive volume delta."
            )

        mapped_box = (
            result.mapped_faces.BoundingBox()
        )

        max_extent = max(
            mapped_box.xlen,
            mapped_box.ylen,
            mapped_box.zlen,
        )

        # Diagnostic guard: unlike the previous tiny result,
        # the mapped decoration must occupy a visible physical span.
        if max_extent < 12.0:
            raise RuntimeError(
                f"{name}: mapped decoration is still too small "
                f"({max_extent:.3f} mm max extent)."
            )

        print(
            name,
            result.mode,
            "delta",
            round(delta, 6),
            "mapped-max",
            round(max_extent, 3),
            "mm",
            "solids",
            len(solids),
            "OK",
        )

    print(
        "-----------------------------------"
    )
    print(
        "Organic diagnostic: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
