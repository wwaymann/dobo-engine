from __future__ import annotations

import os

from .gallery_phase_1 import build_gallery


def main() -> None:
    print()
    print("DOBO Surface Designer - Phase 1")
    print("High-Level Surface Tools")
    print("-----------------------------------")

    outputs = build_gallery()

    if len(outputs) != 4:
        raise RuntimeError(
            "Surface Designer Phase 1 must produce four models."
        )

    for path, result in outputs:
        result.validate()

        size = os.path.getsize(path)
        if size <= 0:
            raise RuntimeError(f"{path}: empty STEP.")

        solids = tuple(result.shape.Solids())
        if len(solids) != 1:
            raise RuntimeError(
                f"{path}: expected exactly one connected output solid, "
                f"got {len(solids)}."
            )

        print(
            os.path.basename(path),
            result.source_kind,
            result.operation,
            "solids",
            len(solids),
            size,
            "bytes",
            "OK",
        )

    print("-----------------------------------")
    print("Models: 4")
    print("Surface Designer Phase 1: Valid OK")
    print()


if __name__ == "__main__":
    main()
