from __future__ import annotations

import os

from .gallery_phase_2 import (
    build_gallery,
)
from .text_outlines import (
    TextOutlineExtractor,
)


def main() -> None:
    print()
    print(
        "DOBO Surface Designer - Phase 2"
    )
    print(
        "Real Text on Surface"
    )
    print(
        "-----------------------------------"
    )

    extractor = (
        TextOutlineExtractor()
    )

    document = (
        extractor.extract(
            "DOBO",
            size=12.0,
            font="Arial",
            document_id=(
                "text_outline_test"
            ),
        )
    )

    document.validate()

    if len(
        document.contours
    ) < 6:
        raise RuntimeError(
            "Expected real glyph outer/inner contours."
        )

    print(
        "Real text contours:",
        len(
            document.contours
        ),
        "OK",
    )

    outputs = build_gallery()

    if len(outputs) != 3:
        raise RuntimeError(
            "Surface Designer Phase 2 must produce three models."
        )

    for path, result in outputs:
        result.validate()

        if (
            result.source_kind
            != "text"
        ):
            raise RuntimeError(
                f"{path}: expected real text source."
            )

        if (
            result.metadata.get(
                "approximation"
            )
            is not False
        ):
            raise RuntimeError(
                f"{path}: text must not be proxy geometry."
            )

        solids = tuple(
            result.shape.Solids()
        )

        if len(solids) != 1:
            raise RuntimeError(
                f"{path}: expected one connected output solid, "
                f"got {len(solids)}."
            )

        size = os.path.getsize(
            path
        )

        if size <= 0:
            raise RuntimeError(
                f"{path}: empty STEP."
            )

        print(
            os.path.basename(
                path
            ),
            "loops",
            result.metadata.get(
                "loop_count"
            ),
            "solids",
            len(solids),
            size,
            "bytes",
            "OK",
        )

    print(
        "-----------------------------------"
    )
    print(
        "Models: 3"
    )
    print(
        "Surface Designer Phase 2: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
