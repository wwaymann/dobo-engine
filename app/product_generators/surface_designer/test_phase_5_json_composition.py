from __future__ import annotations

import os
from .gallery_phase_5_json_composition import build_json_product


def main() -> None:
    result = build_json_product()
    if not result.shape.isValid():
        raise RuntimeError("Phase 5 result is invalid.")
    if result.solids != 1:
        raise RuntimeError("Phase 5 result must contain exactly one solid.")
    if result.faces < 1 or result.volume_final <= 0.0:
        raise RuntimeError("Phase 5 result has invalid topology/volume.")
    if not os.path.isfile(result.path):
        raise RuntimeError("Phase 5 STEP file was not created.")
    expected = {
        "body:phase4_organic",
        "primitives",
        "booleans",
        "geometric_decoration",
        "text:emboss",
        "svg:deboss",
    }
    if set(result.operations) != expected:
        raise RuntimeError(f"Unexpected operations: {result.operations}")
    print("JSON-driven complete model", result.solids, os.path.getsize(result.path), "bytes OK")


if __name__ == "__main__":
    main()
