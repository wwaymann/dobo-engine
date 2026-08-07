from __future__ import annotations

import os

from .gallery_phase_4_hybrid import (
    build_hybrid_showcase,
)


def main() -> None:
    print()
    print(
        "DOBO Surface Designer - Phase 4"
    )
    print(
        "Hybrid Integration Stress Test"
    )
    print(
        "-----------------------------------"
    )

    result = build_hybrid_showcase()

    shape = result["shape"]

    if not shape.isValid():
        raise RuntimeError(
            "Final hybrid model is invalid."
        )

    if result["solids"] != 1:
        raise RuntimeError(
            "Expected exactly one final solid."
        )

    # Primitive fusion must add material.
    if not (
        result["volume_hybrid"]
        > result["volume_organic"]
    ):
        raise RuntimeError(
            "Primitive fusion did not increase volume."
        )

    # Subtractive Boolean stage must remove material.
    if not (
        result["volume_boolean"]
        < result["volume_hybrid"]
    ):
        raise RuntimeError(
            "Boolean cuts did not decrease volume."
        )

    # Geometric decorations must add material.
    if not (
        result["volume_geometric"]
        > result["volume_boolean"]
    ):
        raise RuntimeError(
            "Geometric decoration did not increase volume."
        )

    # Text emboss must add material.
    if not (
        result["volume_text"]
        > result["volume_geometric"]
    ):
        raise RuntimeError(
            "Text emboss did not increase volume."
        )

    # SVG deboss must remove material.
    if not (
        result["final_volume"]
        < result["volume_text"]
    ):
        raise RuntimeError(
            "SVG deboss did not decrease volume."
        )

    size = os.path.getsize(
        result["path"]
    )

    if size <= 0:
        raise RuntimeError(
            "Final STEP file is empty."
        )

    print(
        "Organic core:",
        round(
            result["volume_organic"],
            3,
        ),
        "mm3",
        "OK",
    )

    print(
        "Primitive fusion:",
        round(
            result["volume_hybrid"],
            3,
        ),
        "mm3",
        "OK",
    )

    print(
        "Boolean cuts:",
        round(
            result["volume_boolean"],
            3,
        ),
        "mm3",
        "OK",
    )

    print(
        "Geometric decoration:",
        round(
            result["volume_geometric"],
            3,
        ),
        "mm3",
        "OK",
    )

    print(
        "Text emboss:",
        round(
            result["volume_text"],
            3,
        ),
        "mm3",
        "OK",
    )

    print(
        "SVG deboss / final:",
        round(
            result["final_volume"],
            3,
        ),
        "mm3",
        "OK",
    )

    print(
        "Final faces:",
        result["faces"],
    )

    print(
        "Final solids:",
        result["solids"],
    )

    print(
        "STEP:",
        size,
        "bytes",
        "OK",
    )

    print(
        "-----------------------------------"
    )
    print(
        "Models: 1"
    )
    print(
        "Phase 4 Hybrid Integration: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
