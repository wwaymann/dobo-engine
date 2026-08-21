from __future__ import annotations

from pathlib import Path
import json

from .hierarchy_engine import HierarchicalFeatureVesselEngine
from .hierarchy_specification import HierarchicalFeatureParser
from .test_phase_2j_proportional_scaling import _alternate


SPEC_PATH = Path(__file__).with_name("phase_2j_2l_adaptive_layout.json")


def main() -> None:
    print("DOBO Organic Shape Engine - Phase 2L")
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    parser = HierarchicalFeatureParser()
    specifications = (parser.parse_dict(data), parser.parse_dict(_alternate(data)))
    for label, specification in zip(("primary", "alternate"), specifications):
        report = HierarchicalFeatureVesselEngine.feature_manufacturability_report(
            specification
        )
        for name, valid in report.checks.items():
            print(label, "manufacturability", name, valid, "OK" if valid else "ERROR")
        print(label, "minimum feature mm", round(report.minimum_feature_mm, 4), "OK")
        print(label, "minimum relief depth mm", round(report.minimum_relief_depth_mm, 4), "OK")
        print(label, "maximum relief depth mm", round(report.maximum_relief_depth_mm, 4), "OK")
        if len(report.checks) < 30:
            raise RuntimeError("Manufacturability contract evaluated insufficient rules.")
        report.validate()
    print("DOBO Organic Shape Engine Phase 2L: Valid OK")


if __name__ == "__main__":
    main()
