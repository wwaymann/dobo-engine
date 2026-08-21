from __future__ import annotations

import json
from pathlib import Path

from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)

from .semantic_compiler import COMPILER_VERSION, SemanticToMotorCompiler
from .semantic_parser import SemanticProgramParser


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")


def main() -> None:
    print()
    print("DOBO Design Interpreter - Phase 3B")
    print("Semantic contract -> deterministic compiler -> Motor DOBO JSON")
    print("-----------------------------------")
    semantic = SemanticProgramParser().parse_file(SPEC_PATH)
    first = SemanticToMotorCompiler.compile(semantic)
    second = SemanticToMotorCompiler.compile(semantic)
    if first.motor_program != second.motor_program:
        raise RuntimeError("Semantic compilation is not deterministic.")
    print("compiler version", COMPILER_VERSION, "OK")
    print("deterministic output", True, "OK")
    print("source program", first.report.source_program_id, "OK")
    print("motor program", first.report.output_program_id, "OK")
    print("compiled features", len(first.report.feature_traces), "OK")
    print("compiled relations", first.report.compiled_relations, "OK")
    print("ignored intentional overlaps", len(first.report.ignored_overlap_pairs), "OK")

    hierarchy = first.motor_program["hierarchy_program"]
    templates = hierarchy["templates"]
    roots = hierarchy["roots"]
    operations = [template["operation"] for template in templates]
    primitive_kinds = sorted({template["kind"] for template in templates})
    minimum_compiled_blend = min(template["blend_mm"] for template in templates)
    print("templates", len(templates), "OK")
    print("roots", len(roots), "OK")
    print("add operations", operations.count("add"), "OK")
    print("subtract operations", operations.count("subtract"), "OK")
    print("primitive kinds", primitive_kinds, "OK")
    print("minimum compiled blend mm", round(minimum_compiled_blend, 4), "OK")
    if len(templates) != 6 or len(roots) != 6:
        raise RuntimeError("Semantic compiler lost design features.")
    if operations.count("add") != 4 or operations.count("subtract") != 2:
        raise RuntimeError("Semantic surface effects compiled incorrectly.")
    if minimum_compiled_blend < 0.6:
        raise RuntimeError("Compiled blend lacks proportional-scale reserve.")
    expected_relation_pairs = (
        ("left_eye", "muzzle"),
        ("muzzle", "nose"),
        ("muzzle", "right_eye"),
    )
    if first.report.ignored_overlap_pairs != expected_relation_pairs:
        raise RuntimeError("Controlled semantic relation pairs were not preserved.")

    encoded = json.dumps(first.motor_program, sort_keys=True, ensure_ascii=False)
    for forbidden in ("source", "assumptions", "ambiguities", "confidence"):
        if f'"{forbidden}"' in encoded:
            raise RuntimeError(
                f"Semantic-only field '{forbidden}' leaked into Motor JSON."
            )
    print("semantic metadata isolated", True, "OK")

    motor_specification = HierarchicalFeatureParser().parse_dict(
        first.motor_program
    )
    placements = HierarchicalFeatureVesselEngine.placements(motor_specification)
    anchor_checks = HierarchicalFeatureVesselEngine.surface_anchor_checks(
        motor_specification
    )
    layout = HierarchicalFeatureVesselEngine.layout_report(motor_specification)
    manufacturing = (
        HierarchicalFeatureVesselEngine.feature_manufacturability_report(
            motor_specification
        )
    )
    layout.validate()
    manufacturing.validate()
    print("Motor parser accepted JSON", True, "OK")
    print("placed features", len(placements), "OK")
    print("surface anchor checks", len(anchor_checks), "OK")
    print("layout checks", len(layout.checks), "OK")
    print("manufacturability checks", len(manufacturing.checks), "OK")
    if len(placements) != 6 or not all(anchor_checks.values()):
        raise RuntimeError("Compiled feature placement validation failed.")
    print("-----------------------------------")
    print("No AI call required OK")
    print("DOBO Design Interpreter Phase 3B: Valid OK")


if __name__ == "__main__":
    main()
