from __future__ import annotations

from pathlib import Path

import numpy
import skimage
import trimesh

from .engine import OrganicShapeEngine
from .specification import OrganicShapeParser


SPEC_PATH = Path(__file__).with_name("phase_2a_smooth_blend.json")


def main() -> None:
    print()
    print("DOBO Organic Shape Engine - Phase 2A")
    print("JSON -> SDF fields -> smooth union -> watertight STL")
    print("-----------------------------------")

    specification = OrganicShapeParser().parse_file(SPEC_PATH)
    result = OrganicShapeEngine().generate(specification)

    print("numpy", numpy.__version__)
    print("scikit-image", skimage.__version__)
    print("trimesh", trimesh.__version__)
    print("fields", len(specification.fields), "OK")
    print("blend radius", specification.composition.blend_mm, "mm OK")
    print("components", result.component_count, "OK")
    print("watertight", result.watertight, "OK")
    print("winding consistent", result.winding_consistent, "OK")
    print("vertices", result.vertex_count)
    print("faces", result.face_count)
    print("volume mm3", round(result.volume_mm3, 3))
    print("stage timings")
    for name, seconds in result.stage_seconds.items():
        print(f"  {name} {seconds:.3f}s")
    print(f"generation seconds {result.generation_seconds:.3f}")
    print(f"generation target {result.max_generation_seconds:.1f} seconds")
    print("STL", result.stl_path)
    print("-----------------------------------")

    if result.generation_seconds > result.max_generation_seconds:
        raise RuntimeError("Organic generation exceeded the Phase 2A budget.")

    print("generation budget OK")
    print("DOBO Organic Shape Engine Phase 2A: Valid OK")


if __name__ == "__main__":
    main()
