from __future__ import annotations

import os

from .gallery_pipeline import (
    build_gallery,
)
from .pipeline import (
    SurfaceFeatureMode,
)


def main() -> None:
    print()
    print(
        "DOBO Surface Feature Pipeline"
    )
    print(
        "Integration Test"
    )
    print(
        "-----------------------------------"
    )

    outputs = build_gallery()

    if len(outputs) != 6:
        raise RuntimeError(
            "Pipeline gallery must produce six models."
        )

    emboss_count = 0
    deboss_count = 0

    for path, result in outputs:
        result.validate()

        size = os.path.getsize(
            path
        )

        if size <= 0:
            raise RuntimeError(
                f"{path}: empty STEP."
            )

        if (
            result.mode
            is SurfaceFeatureMode.EMBOSS
        ):
            emboss_count += 1
            delta = (
                result.final_volume
                - result.base_volume
            )
        else:
            deboss_count += 1
            delta = (
                result.base_volume
                - result.final_volume
            )

        if delta <= 0.0:
            raise RuntimeError(
                f"{path}: unexpected volume delta."
            )

        print(
            os.path.basename(path),
            result.mode.value,
            "features",
            result.feature_solid_count,
            "delta",
            round(delta, 3),
            size,
            "bytes",
            "OK",
        )

    if emboss_count != 3:
        raise RuntimeError(
            "Expected three emboss models."
        )

    if deboss_count != 3:
        raise RuntimeError(
            "Expected three deboss models."
        )

    print(
        "-----------------------------------"
    )
    print(
        "Models: 6"
    )
    print(
        "Pipeline: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
