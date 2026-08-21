from __future__ import annotations

from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)

from .morphological_integration import (
    ADVANCED_MORPHOLOGICAL_INTEGRATION_VERSION,
)
from .phase_7_8_macroblock_matrix import macroblock_a_matrix
from .structural_compiler import StructuralSemanticCompiler
from .structural_vocabulary import StructuralVocabularyResolver


def _check(label: str, actual, expected) -> None:
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected!r}, got {actual!r}.")
    print(label, actual, "OK")


def _walk(roots):
    stack = list(roots)
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.get("children", ()))


def main() -> None:
    print()
    print("DOBO Macroblock A.2 - Advanced Morphological Integration")
    print("relative anchors -> exposed hierarchy -> contextual span interfaces")
    print("-----------------------------------")
    _check(
        "morphological integration version",
        ADVANCED_MORPHOLOGICAL_INTEGRATION_VERSION,
        "A2.1",
    )

    cases = {case.id: case for case in macroblock_a_matrix()}

    branching = cases["branching"]
    structural = StructuralVocabularyResolver.resolve(branching.program)
    structural_by_id = {
        feature.semantic_feature_id: feature for feature in structural.features
    }
    if structural_by_id["left_branch"].anchor.horizontal >= -0.1:
        raise RuntimeError("Left branch lost its semantic parent-local offset.")
    if structural_by_id["right_branch"].anchor.horizontal <= 0.1:
        raise RuntimeError("Right branch lost its semantic parent-local offset.")
    if structural_by_id["left_bud"].anchor.horizontal >= -0.1:
        raise RuntimeError("Left bud lost its semantic parent-local offset.")
    if structural_by_id["right_bud"].anchor.horizontal <= 0.1:
        raise RuntimeError("Right bud lost its semantic parent-local offset.")
    print("branch hierarchy lateral separation", True, "OK")

    branching_compiled = StructuralSemanticCompiler.compile(branching.program)
    branching_nodes = {
        node["id"]: node
        for node in _walk(
            branching_compiled.motor_program["hierarchy_program"]["roots"]
        )
    }
    for feature_id in ("left_branch", "right_branch", "left_bud", "right_bud"):
        transform = branching_nodes[feature_id]["transform"]
        if float(transform["translate"][1]) >= 0.0:
            raise RuntimeError(f"{feature_id} is still buried inside its parent.")
        if float(transform["scale"][1]) > 1.05:
            raise RuntimeError(f"{feature_id} depth was over-expanded.")
    print("raised hierarchy exposure", True, "OK")

    architectural = cases["architectural"]
    architectural_compiled = StructuralSemanticCompiler.compile(architectural.program)
    organic_feet = [
        template
        for template in architectural_compiled.motor_program["hierarchy_program"]
        ["templates"]
        if template["id"].endswith("_fusion_foot_template")
    ]
    if not organic_feet or {template["kind"] for template in organic_feet} != {
        "ellipsoid"
    }:
        raise RuntimeError("Organic spans did not receive smooth ellipsoidal shoulders.")
    print("organic span shoulders", len(organic_feet), "OK")

    perforated = cases["perforated"]
    perforated_compiled = StructuralSemanticCompiler.compile(perforated.program)
    geometric_feet = [
        template
        for template in perforated_compiled.motor_program["hierarchy_program"]
        ["templates"]
        if template["id"].endswith("_fusion_foot_template")
    ]
    if not geometric_feet or {template["kind"] for template in geometric_feet} != {
        "rounded_box"
    }:
        raise RuntimeError("Geometric spans lost their style-specific interfaces.")
    print("geometric span shoulders", len(geometric_feet), "OK")

    portal_nodes = {
        node["id"]: node
        for node in _walk(perforated_compiled.motor_program["hierarchy_program"]["roots"])
    }
    portal_cavity_z = float(portal_nodes["portal_cavity"]["transform"]["translate"][2])
    inner_recess_z = float(portal_nodes["inner_recess"]["transform"]["translate"][2])
    if abs(portal_cavity_z) >= 1.5 or abs(inner_recess_z) >= 1.0:
        raise RuntimeError("Nested negative volumes drifted away from semantic centering.")
    print("nested negative centering", True, "OK")

    for case in cases.values():
        compilation = StructuralSemanticCompiler.compile(case.program)
        specification = HierarchicalFeatureParser().parse_dict(
            compilation.motor_program
        )
        anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
        if not all(anchors.values()):
            raise RuntimeError(f"{case.label} surface anchors failed after A.2.")
        layout = HierarchicalFeatureVesselEngine.layout_report(specification)
        manufacturing = (
            HierarchicalFeatureVesselEngine.feature_manufacturability_report(
                specification
            )
        )
        layout.validate()
        manufacturing.validate()
        print(
            case.label,
            "anchor checks",
            len(anchors),
            "layout checks",
            len(layout.checks),
            "manufacturability checks",
            len(manufacturing.checks),
            "OK",
        )

    print("-----------------------------------")
    print("No mesh production or API credit required OK")
    print("DOBO Macroblock A.2 Morphological Integration: Valid OK")


if __name__ == "__main__":
    main()
