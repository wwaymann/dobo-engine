from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .proposal_repair import REPAIR_VERSION, SemanticProposalRepairer
from .semantic_parser import SemanticProgramParser


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")


def _must_reject(label: str, action) -> None:
    try:
        action()
    except (TypeError, ValueError, RuntimeError):
        print("reject", label, True, "OK")
        return
    raise RuntimeError(f"Phase 3E accepted invalid case '{label}'.")


def _repair_probe() -> dict:
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    data["id"] = "bear_planter_repair_probe"
    data["manufacturing"]["maximum_relief_depth_mm"] = 6.0
    for feature in data["features"]:
        if feature["id"] in {"left_ear", "right_ear"}:
            feature["anchor"]["vertical"] = 0.88
            feature["size"]["width_ratio"] = 0.24
            feature["size"]["height_ratio"] = 0.22
        if feature["id"] == "muzzle":
            feature["anchor"]["vertical"] = 0.02
    data["features"][0]["can_omit"] = True
    data["features"][0]["size"]["depth_mm"] = 7.0
    data["assumptions"][0]["requires_confirmation"] = True
    return data


def main() -> None:
    print()
    print("DOBO Design Interpreter - Phase 3E")
    print("Semantic proposal -> validation -> deterministic repair -> Motor JSON")
    print("-----------------------------------")
    repairer = SemanticProposalRepairer()
    fixture = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    unchanged = repairer.repair_dict(fixture)
    print("repair version", unchanged.report.repair_version, "OK")
    print("valid proposal unchanged", not unchanged.report.changed, "OK")
    print("valid proposal attempts", unchanged.report.attempts, "OK")
    print("baseline ready", unchanged.report.ready_for_compilation, "OK")

    repaired = repairer.repair_dict(_repair_probe())
    repaired.report.validate()
    print("invalid proposal repaired", repaired.report.changed, "OK")
    print("repair actions", len(repaired.report.actions), "OK")
    print("repair attempts", repaired.report.attempts, "OK")
    print("surface anchor failures", len(repaired.report.after.surface_anchor_failures), "OK")
    print("layout failures", len(repaired.report.after.layout_failures), "OK")
    print(
        "manufacturability failures",
        len(repaired.report.after.manufacturability_failures),
        "OK",
    )
    print("confirmation fields", len(repaired.report.confirmation_fields), "OK")
    print("ambiguity questions", len(repaired.report.ambiguity_questions), "OK")
    print(
        "required feature preserved",
        repaired.program.features[0].priority == "required"
        and not repaired.program.features[0].can_omit,
        "OK",
    )
    print(
        "relations preserved",
        len(repaired.program.relations) == len(fixture["relations"]),
        "OK",
    )
    print(
        "source identity preserved",
        repaired.program.source.prompt == fixture["source"]["prompt"],
        "OK",
    )
    print(
        "maximum relief below wall",
        repaired.program.manufacturing.maximum_relief_depth_mm
        < repaired.program.manufacturing.minimum_wall_mm,
        "OK",
    )

    second_pass = repairer.repair(repaired.program)
    print("repair idempotent", not second_pass.report.changed, "OK")
    print(
        "compiler output ready",
        second_pass.compilation.report.output_program_id
        == f"compiled_{repaired.program.id}",
        "OK",
    )

    with TemporaryDirectory() as directory:
        program_path = repaired.write_program(Path(directory) / "repaired.json")
        report_path = repaired.write_report(Path(directory) / "repair_report.json")
        parsed = SemanticProgramParser().parse_file(program_path)
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        print("repaired JSON round trip", parsed.id == repaired.program.id, "OK")
        print("machine-readable report", report_data["repair_version"] == REPAIR_VERSION, "OK")

    unknown = deepcopy(fixture)
    unknown["motor_specific_override"] = True
    _must_reject("unknown field", lambda: repairer.repair_dict(unknown))
    broken_relation = deepcopy(fixture)
    broken_relation["relations"][0]["object_id"] = "missing_feature"
    _must_reject(
        "unknown relation reference",
        lambda: repairer.repair_dict(broken_relation),
    )
    wrong_type = deepcopy(fixture)
    wrong_type["manufacturing"]["minimum_wall_mm"] = "four"
    _must_reject("non-numeric wall", lambda: repairer.repair_dict(wrong_type))
    print("-----------------------------------")
    print("No AI call required OK")
    print("DOBO Design Interpreter Phase 3E: Valid OK")


if __name__ == "__main__":
    main()
