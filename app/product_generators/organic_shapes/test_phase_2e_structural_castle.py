from __future__ import annotations

from pathlib import Path

from .structural_engine import StructuralVesselEngine
from .structural_specification import StructuralVesselParser


SPEC_PATH = Path(__file__).with_name("phase_2e_structural_castle.json")


def main() -> None:
    print()
    print("DOBO Organic Shape Engine - Phase 2E")
    print("JSON structural vocabulary -> castle vessel -> refined STL")
    print("-----------------------------------")
    specification = StructuralVesselParser().parse_file(SPEC_PATH)
    engine = StructuralVesselEngine()
    result = engine.generate(specification)
    structural_checks = engine.structural_checks(specification)

    print("components", result.component_count, "OK")
    print("watertight", result.watertight, "OK")
    print("winding consistent", result.winding_consistent, "OK")
    print("structural additions", len(specification.structure.additions), "OK")
    print("structural cutouts", len(specification.structure.cutouts), "OK")
    for name, valid in structural_checks.items():
        print("structure", name, valid, "OK" if valid else "ERROR")
    failed = [name for name, valid in structural_checks.items() if not valid]
    if failed:
        raise RuntimeError(f"Structural composition checks failed: {failed}")
    for name, valid in result.semantic_checks.items():
        print("vessel semantic", name, valid, "OK" if valid else "ERROR")
    print("flat base vertices", result.flat_base_vertex_count, "OK")
    print("vertices", result.vertex_count)
    print("faces", result.face_count)
    print("volume mm3", round(result.volume_mm3, 3))
    if result.mesh_quality is None:
        raise RuntimeError("Structural castle did not execute mesh refinement.")
    print(
        "rim roughness improvement percent",
        round(result.mesh_quality.roughness_improvement_percent, 3),
        "OK",
    )
    print(
        "total volume drift percent",
        round(result.mesh_quality.total_volume_drift_percent, 5),
        "OK",
    )
    print("stage timings")
    for name, seconds in result.stage_seconds.items():
        print(f"  {name} {seconds:.3f}s")
    print(f"generation seconds {result.generation_seconds:.3f}")
    print(f"generation target {result.max_generation_seconds:.1f} seconds")
    print("STL", result.stl_path)
    print("-----------------------------------")
    if result.generation_seconds > result.max_generation_seconds:
        raise RuntimeError("Structural castle exceeded the Phase 2E budget.")
    print("generation budget OK")
    print("DOBO Organic Shape Engine Phase 2E: Valid OK")


if __name__ == "__main__":
    main()
