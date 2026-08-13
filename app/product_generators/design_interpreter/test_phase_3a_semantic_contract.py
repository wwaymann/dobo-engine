from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .semantic_parser import SemanticProgramParser


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")
SCHEMA_PATH = Path(__file__).with_name("semantic_program.schema.json")


def _must_reject(parser, data, label: str) -> None:
    try:
        parser.parse_dict(data)
    except (TypeError, ValueError):
        print("reject", label, True, "OK")
        return
    raise RuntimeError(f"Phase 3A accepted invalid case '{label}'.")


def main() -> None:
    print()
    print("DOBO Design Interpreter - Phase 3A")
    print("Prompt/image meaning -> canonical semantic design contract")
    print("-----------------------------------")
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    parser = SemanticProgramParser()
    program = parser.parse_dict(data)
    print("schema version", program.schema_version, "OK")
    print("machine-readable schema", schema["title"], "OK")
    print("product kind", program.product_kind, "OK")
    print("body family", program.body.family, "OK")
    print("features", len(program.features), "OK")
    print("relations", len(program.relations), "OK")
    print("assumptions", len(program.assumptions), "OK")
    print("non-blocking ambiguities", len(program.ambiguities), "OK")
    print("manufacturing drainage", program.manufacturing.drainage_required, "OK")
    if len(program.features) != 6 or len(program.relations) != 5:
        raise RuntimeError("Phase 3A semantic fixture is incomplete.")

    round_trip_data = json.loads(
        json.dumps(program.to_dict(), ensure_ascii=False)
    )
    round_trip = parser.parse_dict(round_trip_data)
    if round_trip != program:
        raise RuntimeError("Semantic program did not survive canonical round trip.")
    print("canonical round trip", True, "OK")

    unknown_field = deepcopy(data)
    unknown_field["motor_primitive"] = "ellipsoid_sdf"
    _must_reject(parser, unknown_field, "unknown motor-specific field")

    missing_reference = deepcopy(data)
    missing_reference["relations"][0]["object_id"] = "missing_feature"
    _must_reject(parser, missing_reference, "unknown relation reference")

    blocking_ambiguity = deepcopy(data)
    blocking_ambiguity["ambiguities"][0]["blocking"] = True
    _must_reject(parser, blocking_ambiguity, "blocking ambiguity")

    unsafe_depth = deepcopy(data)
    unsafe_depth["manufacturing"]["maximum_relief_depth_mm"] = 4.2
    _must_reject(parser, unsafe_depth, "relief deeper than wall")

    omittable_required = deepcopy(data)
    omittable_required["features"][0]["can_omit"] = True
    _must_reject(parser, omittable_required, "omittable required feature")

    wrong_boolean_type = deepcopy(data)
    wrong_boolean_type["manufacturing"]["drainage_required"] = "true"
    _must_reject(parser, wrong_boolean_type, "non-boolean manufacturing flag")

    print("-----------------------------------")
    print("No SDF, mesh or engine primitive required OK")
    print("DOBO Design Interpreter Phase 3A: Valid OK")


if __name__ == "__main__":
    main()
