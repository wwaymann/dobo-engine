from __future__ import annotations

from pathlib import Path

from .vessel_engine import OrganicVesselEngine
from .vessel_specification import OrganicVesselParser


SPEC_PATH = Path(__file__).with_name("phase_2b_organic_vessel.json")


def main() -> None:
    print()
    print("DOBO Organic Shape Engine - Phase 2B")
    print("Envelope -> cavity/opening -> flat base/drain -> STL")
    print("-----------------------------------")
    specification = OrganicVesselParser().parse_file(SPEC_PATH)
    result = OrganicVesselEngine().generate(specification)

    print("envelope fields", len(specification.fields), "OK")
    print("components", result.component_count, "OK")
    print("watertight", result.watertight, "OK")
    print("winding consistent", result.winding_consistent, "OK")
    print("nominal wall", result.nominal_wall_mm, "mm OK")
    print("structural bottom", result.bottom_mm, "mm OK")
    print("rim round", specification.vessel.rim_round_mm, "mm OK")
    print("flat base z", result.flat_base_z_mm, "mm")
    print("flat base vertices", result.flat_base_vertex_count, "OK")
    for name, valid in result.semantic_checks.items():
        print("semantic", name, valid, "OK" if valid else "ERROR")
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
        raise RuntimeError("Organic vessel generation exceeded the Phase 2B budget.")
    print("generation budget OK")
    print("DOBO Organic Shape Engine Phase 2B: Valid OK")


if __name__ == "__main__":
    main()
