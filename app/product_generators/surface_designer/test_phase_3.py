from __future__ import annotations

import os

from .gallery_phase_3 import (
    build_gallery,
)


EXPECTED = {
    "text_cone.step",
    "svg_cone.step",
    "text_sphere.step",
    "svg_sphere.step",
    "text_torus.step",
    "svg_torus.step",
    "text_organic.step",
    "svg_organic.step",
}


def main() -> None:
    print()
    print(
        "DOBO Surface Designer - Phase 3"
    )
    print(
        "Universal Native Surface Decoration"
    )
    print(
        "-----------------------------------"
    )

    outputs = build_gallery()

    if len(outputs) != 8:
        raise RuntimeError(
            "Phase 3 must generate exactly eight models."
        )

    names = set()

    for path, result in outputs:
        result.validate()

        filename = os.path.basename(
            path
        )

        names.add(
            filename
        )

        solids = tuple(
            result.shape.Solids()
        )

        if len(solids) != 1:
            raise RuntimeError(
                f"{filename}: expected one connected final solid."
            )

        size = os.path.getsize(
            path
        )

        if size <= 0:
            raise RuntimeError(
                f"{filename}: empty STEP."
            )

        delta = (
            result.final_volume
            - result.base_volume
            if result.mode == "emboss"
            else result.base_volume
            - result.final_volume
        )

        if delta <= 1e-8:
            raise RuntimeError(
                f"{filename}: expected positive volume delta."
            )

        print(
            filename,
            result.mode,
            "delta",
            round(
                delta,
                6,
            ),
            "solids",
            len(solids),
            size,
            "bytes",
            "OK",
        )

    if names != EXPECTED:
        raise RuntimeError(
            f"Unexpected Phase 3 outputs: {sorted(names)}"
        )

    print(
        "-----------------------------------"
    )
    print(
        "Models: 8"
    )
    print(
        "Phase 3: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
