from __future__ import annotations

import os

from .gallery_phase_3_4 import (
    build_gallery,
)
from .surface_feature_api import (
    SurfaceFeatureMode,
)


def main() -> None:
    print()
    print(
        "DOBO Advanced Geometry - Phase 3.4"
    )
    print(
        "Reusable Surface Feature API"
    )
    print(
        "-----------------------------------"
    )

    outputs = build_gallery()

    if len(outputs) != 6:
        raise RuntimeError(
            "Phase 3.4 gallery must produce six models."
        )

    for path, result in outputs:
        result.validate()

        if result.loop_count != 3:
            raise RuntimeError(
                f"{path}: expected outer/hole/island topology."
            )

        # The corrected architecture composes topology into
        # one tool before touching the base body.
        if result.boolean_count != 1:
            raise RuntimeError(
                f"{path}: expected one final model Boolean."
            )

        size = os.path.getsize(
            path
        )

        if size <= 0:
            raise RuntimeError(
                f"{path}: empty STEP."
            )

        delta = (
            result.final_volume
            - result.base_volume
            if result.mode
            is SurfaceFeatureMode.EMBOSS
            else result.base_volume
            - result.final_volume
        )

        if delta <= 0.0:
            raise RuntimeError(
                f"{path}: unexpected volume delta."
            )

        print(
            os.path.basename(path),
            result.mode.value,
            "loops",
            result.loop_count,
            "model-booleans",
            result.boolean_count,
            "delta",
            round(delta, 3),
            size,
            "bytes",
            "OK",
        )

    print(
        "-----------------------------------"
    )
    print(
        "Models: 6"
    )
    print(
        "Phase 3.4: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
