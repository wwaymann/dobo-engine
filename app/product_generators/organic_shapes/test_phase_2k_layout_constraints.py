from __future__ import annotations

from pathlib import Path
import json

from .hierarchy_engine import HierarchicalFeatureVesselEngine
from .hierarchy_specification import HierarchicalFeatureParser
from .test_phase_2j_proportional_scaling import _alternate


SPEC_PATH = Path(__file__).with_name("phase_2j_2l_adaptive_layout.json")


def main() -> None:
    print("DOBO Organic Shape Engine - Phase 2K")
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    parser = HierarchicalFeatureParser()
    specifications = (parser.parse_dict(data), parser.parse_dict(_alternate(data)))
    for label, specification in zip(("primary", "alternate"), specifications):
        report = HierarchicalFeatureVesselEngine.layout_report(specification)
        for name, valid in report.checks.items():
            print(label, "layout", name, valid, "OK" if valid else "ERROR")
        print(label, "evaluated pairs", report.evaluated_pairs, "OK")
        print(label, "ignored intentional pairs", report.ignored_pairs, "OK")
        print(
            label,
            "minimum pair clearance mm",
            round(report.minimum_pair_clearance_mm, 4),
            "OK",
        )
        if report.evaluated_pairs < 15 or report.ignored_pairs != 4:
            raise RuntimeError("Layout contract did not evaluate the expected pairs.")
        report.validate()
    print("DOBO Organic Shape Engine Phase 2K: Valid OK")


if __name__ == "__main__":
    main()
