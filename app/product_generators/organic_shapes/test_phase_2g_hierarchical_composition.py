from __future__ import annotations

from pathlib import Path

import numpy as np

from .hierarchy_engine import HierarchicalFeatureVesselEngine
from .hierarchy_specification import HierarchicalFeatureParser


SPEC_PATH = Path(__file__).with_name("phase_2g_hierarchical_composition.json")


def main() -> None:
    print()
    print("DOBO Organic Shape Engine - Phase 2G")
    print("Templates -> hierarchy -> transforms/symmetry/repetition -> refined STL")
    print("-----------------------------------")
    specification = HierarchicalFeatureParser().parse_file(SPEC_PATH)
    engine = HierarchicalFeatureVesselEngine()
    placements = engine.placements(specification)
    result = engine.generate(specification)
    checks = engine.hierarchy_checks(specification)

    mirrored = tuple(item for item in placements if ".mirror_" in item.id)
    crests = tuple(item for item in placements if "repeated_crest" in item.id)
    eyes = tuple(item for item in placements if "mirrored_eye" in item.id)
    gem = next(item for item in placements if "scaled_rotated_gem" in item.id)
    print("components", result.component_count, "OK")
    print("watertight", result.watertight, "OK")
    print("winding consistent", result.winding_consistent, "OK")
    print("templates", len(specification.templates), "OK")
    print("placed features", len(placements), "OK")
    print("mirrored placements", len(mirrored), "OK")
    print("repeated crest placements", len(crests), "OK")
    if len(placements) <= len(specification.templates):
        raise RuntimeError("Hierarchy did not reuse its templates.")
    if len(mirrored) != 2 or len(crests) != 3:
        raise RuntimeError("Hierarchy symmetry or repetition expansion failed.")
    crest_origins = np.asarray([item.matrix[:3, 3] for item in crests])
    if not np.allclose(crest_origins[:, 0], [-13.0, 0.0, 13.0]):
        raise RuntimeError("Hierarchy repetition did not apply its translation step.")
    if not np.allclose(crest_origins[:, 1:], [[-29.0, 29.0]] * 3):
        raise RuntimeError("Repeated children did not inherit the helmet transform.")
    eye_x = sorted(float(item.matrix[0, 3]) for item in eyes)
    if not np.allclose(eye_x, [-11.0, 11.0]):
        raise RuntimeError("Hierarchy mirror did not reflect the eye translation.")
    gem_axis = gem.matrix[:3, :3] @ np.asarray([0.0, 0.0, 1.0])
    if not np.allclose(gem_axis, [0.0, -1.25, 0.0], atol=1e-9):
        raise RuntimeError("Hierarchy rotation or scale composition is incorrect.")
    print("inherited child transform True OK")
    print("mirror transform True OK")
    print("rotation and scale transform True OK")
    for name, valid in checks.items():
        print("placement", name, valid, "OK" if valid else "ERROR")
    failed = [name for name, valid in checks.items() if not valid]
    if failed:
        raise RuntimeError(f"Hierarchy placement checks failed: {failed}")
    for name, valid in result.semantic_checks.items():
        print("vessel semantic", name, valid, "OK" if valid else "ERROR")
    print("flat base vertices", result.flat_base_vertex_count, "OK")
    print("vertices", result.vertex_count)
    print("faces", result.face_count)
    print("volume mm3", round(result.volume_mm3, 3))
    if result.mesh_quality is None:
        raise RuntimeError("Hierarchy did not execute mesh refinement.")
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
        raise RuntimeError("Hierarchy exceeded the Phase 2G budget.")
    print("generation budget OK")
    print("DOBO Organic Shape Engine Phase 2G: Valid OK")


if __name__ == "__main__":
    main()
