from __future__ import annotations

from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)

from .phase_7_8_macroblock_matrix import macroblock_a_matrix
from .structural_compiler import StructuralSemanticCompiler
from .visible_morphological_continuity import (
    VISIBLE_MORPHOLOGICAL_CONTINUITY_VERSION,
)


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


def _length(vector) -> float:
    return sum(float(value) ** 2 for value in vector) ** 0.5


def main() -> None:
    print()
    print("DOBO Macroblock A.4 - Visible Morphological Continuity")
    print("root flare -> hierarchy bridge -> visible span shoulders -> acceptance")
    print("-----------------------------------")
    _check(
        "visible continuity version",
        VISIBLE_MORPHOLOGICAL_CONTINUITY_VERSION,
        "A4.1",
    )

    cases = {case.id: case for case in macroblock_a_matrix()}
    branching = StructuralSemanticCompiler.compile(cases["branching"].program)
    hierarchy = branching.motor_program["hierarchy_program"]
    templates = {item["id"]: item for item in hierarchy["templates"]}
    nodes = {node["id"]: node for node in _walk(hierarchy["roots"])}

    expected_flare_nodes = {
        "central_trunk",
        "left_branch",
        "right_branch",
        "left_bud",
        "right_bud",
    }
    flare_nodes = set()
    for node_id in expected_flare_nodes:
        ids = [
            value
            for value in nodes[node_id].get("template_ids", ())
            if value.endswith("_visible_root_flare_template")
        ]
        if len(ids) != 1:
            raise RuntimeError(f"{node_id} must own exactly one visible A.4 root flare.")
        flare = templates[ids[0]]
        if float(flare["center"][1]) >= 0.0:
            raise RuntimeError(f"{node_id} visible root flare did not reach outward.")
        if flare["operation"] != "add":
            raise RuntimeError(f"{node_id} visible root flare must be additive.")
        flare_nodes.add(node_id)
    _check("visible branch root flares", len(flare_nodes), 5)

    bridges = [
        template
        for template in hierarchy["templates"]
        if template["id"].endswith("_visible_bridge_template")
    ]
    _check("visible hierarchy bridges", len(bridges), 4)
    for bridge in bridges:
        if bridge["kind"] != "capsule" or bridge["operation"] != "add":
            raise RuntimeError("A.4 hierarchy bridge lost its additive capsule contract.")
        if _length(bridge["end"]) <= _length(bridge["start"]):
            raise RuntimeError("A.4 hierarchy bridge does not advance toward its child.")
        if float(bridge["radius_mm"]) < 0.9 * cases["branching"].program.manufacturing.minimum_feature_mm:
            raise RuntimeError("A.4 hierarchy bridge is below its printable radius reserve.")
    print("bridge geometry continuous", True, "OK")

    if any(
        "visible_root_flare" in value or "visible_bridge" in value
        for value in nodes["bud_inset"].get("template_ids", ())
    ):
        raise RuntimeError("A.4 must not add material around a negative-volume child.")
    print("negative volumes protected", True, "OK")

    architectural = StructuralSemanticCompiler.compile(cases["architectural"].program)
    architectural_templates = architectural.motor_program["hierarchy_program"]["templates"]
    organic_span_roots = [
        item
        for item in architectural_templates
        if item["id"].endswith("_visible_span_root_template")
    ]
    _check("organic visible span roots", len(organic_span_roots), 6)
    if {item["kind"] for item in organic_span_roots} != {"ellipsoid"}:
        raise RuntimeError("Organic A.4 span roots must remain ellipsoidal.")
    if max(float(item["center"][1]) for item in organic_span_roots) >= 0.0:
        raise RuntimeError("Organic A.4 span roots did not reach the visible skin.")
    print("organic span root exposure", True, "OK")

    perforated = StructuralSemanticCompiler.compile(cases["perforated"].program)
    geometric_span_roots = [
        item
        for item in perforated.motor_program["hierarchy_program"]["templates"]
        if item["id"].endswith("_visible_span_root_template")
    ]
    _check("geometric visible span roots", len(geometric_span_roots), 2)
    if {item["kind"] for item in geometric_span_roots} != {"rounded_box"}:
        raise RuntimeError("Geometric A.4 span roots lost planar style character.")
    print("geometric style preservation", True, "OK")

    for case in cases.values():
        compilation = StructuralSemanticCompiler.compile(case.program)
        specification = HierarchicalFeatureParser().parse_dict(compilation.motor_program)
        anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
        if not all(anchors.values()):
            raise RuntimeError(f"{case.label} surface anchors failed after A.4.")
        layout = HierarchicalFeatureVesselEngine.layout_report(specification)
        manufacturing = HierarchicalFeatureVesselEngine.feature_manufacturability_report(
            specification
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
    print("DOBO Macroblock A.4 Visible Morphological Continuity: Valid OK")


if __name__ == "__main__":
    main()
