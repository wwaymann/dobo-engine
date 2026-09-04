from __future__ import annotations

from pathlib import Path
import json

from .hierarchy_engine import HierarchicalFeatureVesselEngine
from .hierarchy_specification import HierarchicalFeatureParser
from .test_phase_2j_proportional_scaling import _alternate


SPEC_PATH = Path(__file__).with_name("phase_2j_2l_adaptive_layout.json")


def main() -> None:
    print()
    print("DOBO Organic Shape Engine - Phases 2J-2L")
    print("Proportional scale -> layout constraints -> manufacturing preflight -> STL")
    print("-----------------------------------")
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    parser = HierarchicalFeatureParser()
    specification = parser.parse_dict(data)
    alternate = parser.parse_dict(_alternate(data))
    engine = HierarchicalFeatureVesselEngine()
    scaling = engine.proportional_scale_diagnostics(specification)
    layout = engine.layout_report(specification)
    manufacturing = engine.feature_manufacturability_report(specification)
    alternate_layout = engine.layout_report(alternate)
    alternate_manufacturing = engine.feature_manufacturability_report(alternate)
    layout.validate()
    manufacturing.validate()
    alternate_layout.validate()
    alternate_manufacturing.validate()
    print("scaled placements", scaling["scaled_placement_count"], "OK")
    print("protected relief depth", scaling["depth_scale_preserved"], "OK")
    print("layout checks", len(layout.checks), "OK")
    print("manufacturability checks", len(manufacturing.checks), "OK")
    print("alternate layout checks", len(alternate_layout.checks), "OK")
    print(
        "alternate manufacturability checks",
        len(alternate_manufacturing.checks),
        "OK",
    )
    result = engine.generate(specification)
    placement_checks = engine.hierarchy_checks(specification)
    print("components", result.component_count, "OK")
    print("watertight", result.watertight, "OK")
    print("winding consistent", result.winding_consistent, "OK")
    if not all(placement_checks.values()):
        failed = [name for name, valid in placement_checks.items() if not valid]
        raise RuntimeError(f"Consolidated placement checks failed: {failed}")
    for name, valid in result.semantic_checks.items():
        print("vessel semantic", name, valid, "OK" if valid else "ERROR")
    print("vertices", result.vertex_count)
    print("faces", result.face_count)
    print("stage timings")
    for name, seconds in result.stage_seconds.items():
        print(f"  {name} {seconds:.3f}s")
    print(f"generation seconds {result.generation_seconds:.3f}")
    print(f"generation target {result.max_generation_seconds:.1f} seconds")
    print("STL", result.stl_path)
    print("-----------------------------------")
    if result.generation_seconds > result.max_generation_seconds:
        raise RuntimeError("Phases 2J-2L exceeded the generation budget.")
    print("generation budget OK")
    print("DOBO Organic Shape Engine Phases 2J-2L: Valid OK")


if __name__ == "__main__":
    main()
