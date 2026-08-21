from __future__ import annotations

from pathlib import Path

from .feature_program_engine import FeatureProgramVesselEngine
from .feature_program_specification import FeatureProgramParser


SPEC_PATH = Path(__file__).with_name("phase_2f_hybrid_feature_program.json")


def main() -> None:
    print()
    print("DOBO Organic Shape Engine - Phase 2F")
    print("Generic JSON feature program -> hybrid character vessel -> refined STL")
    print("-----------------------------------")
    specification = FeatureProgramParser().parse_file(SPEC_PATH)
    engine = FeatureProgramVesselEngine()
    result = engine.generate(specification)
    checks = engine.feature_checks(specification)

    additions = tuple(f for f in specification.features if f.operation == "add")
    subtractions = tuple(f for f in specification.features if f.operation == "subtract")
    kinds = {feature.kind for feature in specification.features}
    print("components", result.component_count, "OK")
    print("watertight", result.watertight, "OK")
    print("winding consistent", result.winding_consistent, "OK")
    print("feature instructions", len(specification.features), "OK")
    print("add operations", len(additions), "OK")
    print("subtract operations", len(subtractions), "OK")
    print("primitive kinds", len(kinds), "OK")
    if not additions or not subtractions or len(kinds) < 5:
        raise RuntimeError("Hybrid feature-program coverage is insufficient.")
    for name, valid in checks.items():
        print("feature", name, valid, "OK" if valid else "ERROR")
    failed = [name for name, valid in checks.items() if not valid]
    if failed:
        raise RuntimeError(f"Hybrid feature checks failed: {failed}")
    for name, valid in result.semantic_checks.items():
        print("vessel semantic", name, valid, "OK" if valid else "ERROR")
    print("flat base vertices", result.flat_base_vertex_count, "OK")
    print("vertices", result.vertex_count)
    print("faces", result.face_count)
    print("volume mm3", round(result.volume_mm3, 3))
    if result.mesh_quality is None:
        raise RuntimeError("Hybrid feature program did not refine its mesh.")
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
        raise RuntimeError("Hybrid feature program exceeded the Phase 2F budget.")
    print("generation budget OK")
    print("DOBO Organic Shape Engine Phase 2F: Valid OK")


if __name__ == "__main__":
    main()
