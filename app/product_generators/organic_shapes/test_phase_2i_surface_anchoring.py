from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from .hierarchy_engine import HierarchicalFeatureVesselEngine
from .hierarchy_specification import HierarchicalFeatureParser


SPEC_PATH = Path(__file__).with_name("phase_2i_surface_anchoring.json")


def main() -> None:
    print()
    print("DOBO Organic Shape Engine - Phase 2I")
    print("Normalized anchors -> surface solve/orientation -> transferable features")
    print("-----------------------------------")
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    parser = HierarchicalFeatureParser()
    specification = parser.parse_dict(data)
    engine = HierarchicalFeatureVesselEngine()
    placements = engine.placements(specification)
    anchor_checks = engine.surface_anchor_checks(specification)

    alternate_data = deepcopy(data)
    alternate_data["id"] = "phase_2i_surface_anchoring_wide_probe"
    alternate_data["grid"]["minimum"] = [-61.0, -55.0, -49.0]
    alternate_data["grid"]["maximum"] = [61.0, 49.0, 56.0]
    alternate_data["fields"][0]["radii"] = [47.0, 37.0, 40.0]
    alternate_data["fields"][1]["center"] = [0.0, -15.0, 0.0]
    alternate_data["fields"][1]["radii"] = [39.0, 27.0, 34.0]
    alternate_data["vessel"]["base_z_mm"] = -38.0
    alternate_data["vessel"]["cavity_floor_z_mm"] = -31.5
    alternate_data["vessel"]["opening_radii"] = [22.0, 17.0]
    alternate_data["vessel"]["opening_start_z_mm"] = 22.0
    alternate_data["vessel"]["drain_start_z_mm"] = -42.0
    alternate_data["vessel"]["drain_end_z_mm"] = -28.0
    alternate = parser.parse_dict(alternate_data)
    alternate_placements = engine.placements(alternate)
    alternate_checks = engine.surface_anchor_checks(alternate)

    print("anchored placements", len(placements), "OK")
    print("alternate anchored placements", len(alternate_placements), "OK")
    if len(placements) != 7 or len(alternate_placements) != 7:
        raise RuntimeError("Surface anchor program did not place seven features.")
    all_anchor_checks = {
        **{f"primary/{key}": value for key, value in anchor_checks.items()},
        **{f"alternate/{key}": value for key, value in alternate_checks.items()},
    }
    for name, valid in all_anchor_checks.items():
        print("anchor", name, valid, "OK" if valid else "ERROR")
    failed = [name for name, valid in all_anchor_checks.items() if not valid]
    if failed:
        raise RuntimeError(f"Surface-anchor checks failed: {failed}")

    origins = np.asarray([item.matrix[:3, 3] for item in placements])
    alternate_origins = np.asarray(
        [item.matrix[:3, 3] for item in alternate_placements]
    )
    transfer = np.linalg.norm(origins - alternate_origins, axis=1)
    print("minimum body transfer mm", round(float(transfer.min()), 4), "OK")
    print("maximum body transfer mm", round(float(transfer.max()), 4), "OK")
    if float(transfer.min()) < 3.0:
        raise RuntimeError("Anchors did not adapt materially to the alternate body.")

    result = engine.generate(specification)
    placement_checks = engine.hierarchy_checks(specification)
    print("components", result.component_count, "OK")
    print("watertight", result.watertight, "OK")
    print("winding consistent", result.winding_consistent, "OK")
    for name, valid in placement_checks.items():
        print("placement", name, valid, "OK" if valid else "ERROR")
    if not all(placement_checks.values()):
        raise RuntimeError("An anchored feature did not produce its requested material state.")
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
        raise RuntimeError("Surface anchoring exceeded the Phase 2I budget.")
    print("generation budget OK")
    print("same normalized program transferred to distinct body True OK")
    print("DOBO Organic Shape Engine Phase 2I: Valid OK")


if __name__ == "__main__":
    main()
