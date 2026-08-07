from __future__ import annotations

import os

from .gallery import (
    GALLERY_CASES,
    PatternGalleryBuilder,
)


def main() -> None:
    builder = PatternGalleryBuilder()

    print()
    print("DOBO Decorative Patterns Gallery - Phase 5.1")
    print("--------------------------------------------")

    completed = 0

    for case in GALLERY_CASES:
        path = builder.run_case(
            case
        )

        if not os.path.isfile(path):
            raise RuntimeError(
                f"{case.id}: STEP missing."
            )

        print(
            case.id,
            os.path.getsize(path),
            "bytes",
            "OK",
        )

        completed += 1

    print("--------------------------------------------")
    print("STEP models:", completed)
    print("Phase 5.1: Valid OK")
    print()


if __name__ == "__main__":
    main()
