from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .hierarchy_engine import HierarchicalFeatureVesselEngine
from .hierarchy_specification import HierarchicalFeatureParser


SPEC_PATH = Path(__file__).with_name("phase_2j_2l_adaptive_layout.json")


def _alternate(data):
    alternate = deepcopy(data)
    alternate["id"] = "phase_2j_wide_scale_probe"
    alternate["grid"]["minimum"] = [-61.0, -55.0, -68.0]
    alternate["grid"]["maximum"] = [61.0, 49.0, 65.0]
    alternate["fields"][0]["radii"] = [47.0, 37.0, 52.0]
    alternate["fields"][1]["center"] = [0.0, -15.0, 0.0]
    alternate["fields"][1]["radii"] = [39.0, 27.0, 45.0]
    alternate["vessel"]["base_z_mm"] = -54.0
    alternate["vessel"]["cavity_floor_z_mm"] = -47.5
    alternate["vessel"]["opening_radii"] = [22.0, 17.0]
    alternate["vessel"]["opening_start_z_mm"] = 30.0
    alternate["vessel"]["drain_start_z_mm"] = -58.0
    alternate["vessel"]["drain_end_z_mm"] = -44.0
    return alternate


def main() -> None:
    print("DOBO Organic Shape Engine - Phase 2J")
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    parser = HierarchicalFeatureParser()
    engine = HierarchicalFeatureVesselEngine()
    primary = parser.parse_dict(data)
    alternate = parser.parse_dict(_alternate(data))
    primary_metrics = engine.proportional_scale_diagnostics(primary)
    alternate_metrics = engine.proportional_scale_diagnostics(alternate)
    for name, value in primary_metrics.items():
        print("primary", name, value, "OK")
    for name, value in alternate_metrics.items():
        print("alternate", name, value, "OK")
    if primary_metrics["scaled_placement_count"] != 7:
        raise RuntimeError("Primary body did not scale every anchored placement.")
    if alternate_metrics["scaled_placement_count"] != 7:
        raise RuntimeError("Alternate body did not scale every anchored placement.")
    if not primary_metrics["depth_scale_preserved"]:
        raise RuntimeError("Primary body changed the protected relief depth.")
    if not alternate_metrics["depth_scale_preserved"]:
        raise RuntimeError("Alternate body changed the protected relief depth.")
    if alternate_metrics["maximum_scale"] <= primary_metrics["maximum_scale"]:
        raise RuntimeError("Wide body did not increase tangential feature scale.")
    print("DOBO Organic Shape Engine Phase 2J: Valid OK")


if __name__ == "__main__":
    main()
