from __future__ import annotations

from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)

from .continuous_morphological_fusion import (
    CONTINUOUS_MORPHOLOGICAL_FUSION_VERSION,
)
from .phase_7_8_macroblock_matrix import macroblock_a_matrix
from .structural_compiler import StructuralSemanticCompiler


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


def _half_extents(template):
    kind = template["kind"]
    if kind == "ellipsoid":
        return tuple(float(value) for value in template["radii"])
    if kind == "rounded_triangle_prism":
        points = template["vertices_xz"]
        return (
            max(abs(float(point[0])) for point in points),
            float(template["half_depth_mm"]),
            max(abs(float(point[1])) for point in points),
        )
    raise RuntimeError(f"Unsupported A.3 fixture kind {kind!r}.")


def main() -> None:
    print()
    print("DOBO Macroblock A.3 - Continuous Morphological Fusion")
    print("spread -> transition mass -> continuous shoulders -> acceptance")
    print("-----------------------------------")
    _check(
        "continuous fusion version",
        CONTINUOUS_MORPHOLOGICAL_FUSION_VERSION,
        "A3.1",
    )

    cases = {case.id: case for case in macroblock_a_matrix()}
    branching = StructuralSemanticCompiler.compile(cases["branching"].program)
    hierarchy = branching.motor_program["hierarchy_program"]
    templates = {item["id"]: item for item in hierarchy["templates"]}
    nodes = {node["id"]: node for node in _walk(hierarchy["roots"])}

    left_x = float(nodes["left_branch"]["transform"]["translate"][0])
    right_x = float(nodes["right_branch"]["transform"]["translate"][0])
    if left_x > -10.0 or right_x < 10.0:
        raise RuntimeError("Branch attachment spread is still visually collapsed.")
    if abs(left_x + right_x) > 1e-9:
        raise RuntimeError("A.3 branch spread lost bilateral symmetry.")
    print("branch attachment spread", round(abs(left_x), 4), "mm OK")

    expected_transition_nodes = {
        "central_trunk",
        "left_branch",
        "right_branch",
        "left_bud",
        "right_bud",
    }
    transition_nodes = set()
    for node_id in expected_transition_nodes:
        node = nodes[node_id]
        transition_ids = [
            template_id
            for template_id in node.get("template_ids", ())
            if template_id.endswith("_continuous_transition_template")
        ]
        if len(transition_ids) != 1:
            raise RuntimeError(f"{node_id} must own exactly one A.3 transition mass.")
        transition_nodes.add(node_id)
        transition = templates[transition_ids[0]]
        visible = templates[f"{node_id}_template"]
        visible_x, visible_y, visible_z = _half_extents(visible)
        transition_x, transition_y, transition_z = _half_extents(transition)
        if not (transition_x < visible_x and transition_z < visible_z):
            raise RuntimeError(f"{node_id} transition mass swallowed the visible silhouette.")
        if transition_y <= visible_y:
            raise RuntimeError(f"{node_id} transition mass does not reach inward enough.")
        if float(transition["center"][1]) <= 0.0:
            raise RuntimeError(f"{node_id} transition mass does not point into its parent.")
    _check("continuous transition masses", len(transition_nodes), 5)
    print("silhouette-preserving collars", True, "OK")

    negative_nodes = {"bud_inset"}
    for node_id in negative_nodes:
        if any("continuous_transition" in value for value in nodes[node_id]["template_ids"]):
            raise RuntimeError("A.3 must not add material around negative-volume children.")
    print("negative volumes protected", True, "OK")

    architectural = StructuralSemanticCompiler.compile(cases["architectural"].program)
    organic_feet = [
        template
        for template in architectural.motor_program["hierarchy_program"]["templates"]
        if template["id"].endswith("_fusion_foot_template")
    ]
    if not organic_feet:
        raise RuntimeError("A.3 lost organic span shoulders.")
    if min(float(item["center"][1]) for item in organic_feet) < 3.0:
        raise RuntimeError("Organic span shoulders did not move into the body transition zone.")
    if min(float(item["radii"][1]) for item in organic_feet) < 4.7:
        raise RuntimeError("Organic span shoulders remain too shallow for continuous fusion.")
    print("continuous organic span shoulders", len(organic_feet), "OK")

    perforated = StructuralSemanticCompiler.compile(cases["perforated"].program)
    geometric_feet = [
        template
        for template in perforated.motor_program["hierarchy_program"]["templates"]
        if template["id"].endswith("_fusion_foot_template")
    ]
    if {item["kind"] for item in geometric_feet} != {"rounded_box"}:
        raise RuntimeError("Geometric spans lost planar transition character.")
    print("geometric style preservation", len(geometric_feet), "OK")

    for case in cases.values():
        compilation = StructuralSemanticCompiler.compile(case.program)
        specification = HierarchicalFeatureParser().parse_dict(
            compilation.motor_program
        )
        anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
        if not all(anchors.values()):
            raise RuntimeError(f"{case.label} surface anchors failed after A.3.")
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
    print("DOBO Macroblock A.3 Continuous Morphological Fusion: Valid OK")


if __name__ == "__main__":
    main()
