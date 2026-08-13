from __future__ import annotations

import json
from math import sqrt
from pathlib import Path

from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)

from .semantic_parser import SemanticProgramParser
from .structural_compiler import (
    SILHOUETTE_VALIDATION_VERSION,
    STRUCTURAL_ORIENTATION_VERSION,
    VOLUMETRIC_SILHOUETTE_VERSION,
    StructuralSemanticCompiler,
)
from .structural_pipeline import (
    STRUCTURAL_FUSION_VERSION,
    STRUCTURAL_PIPELINE_VERSION,
)


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")


def _body_cross_section_x(field: dict, point: list[float]) -> float:
    center = field["center"]
    radii = field["radii"]
    y_term = ((point[1] - center[1]) / radii[1]) ** 2
    z_term = ((point[2] - center[2]) / radii[2]) ** 2
    remaining = max(0.0, 1.0 - y_term - z_term)
    return abs(center[0]) + radii[0] * sqrt(remaining)


def main() -> None:
    print()
    print("DOBO Visual Acceptance - Phases 4G-4K")
    print("orientation -> volume -> fusion -> silhouette -> pipeline")
    print("-----------------------------------")
    semantic = SemanticProgramParser().parse_dict(
        json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    )
    compiled = StructuralSemanticCompiler.compile(semantic)
    motor = compiled.motor_program
    hierarchy = motor["hierarchy_program"]
    fields = {field["id"]: field for field in motor["fields"]}
    field_ids = set(motor["composition"]["field_ids"])
    ear_ids = {
        "left_ear__silhouette_mass",
        "right_ear__silhouette_mass",
    }
    if not ear_ids <= field_ids:
        raise RuntimeError("Ear masses were not fused into the body composition.")
    if compiled.report.volumetric_silhouette_features != 2:
        raise RuntimeError("Expected two volumetric silhouette features.")
    print("orientation version", STRUCTURAL_ORIENTATION_VERSION, "OK")
    print("volumetric template version", VOLUMETRIC_SILHOUETTE_VERSION, "OK")
    print("fusion version", STRUCTURAL_FUSION_VERSION, "OK")
    print("silhouette validation version", SILHOUETTE_VALIDATION_VERSION, "OK")
    print("pipeline version", STRUCTURAL_PIPELINE_VERSION, "OK")
    print("volumetric ears", compiled.report.volumetric_silhouette_features, "OK")

    template_ids = {template["id"] for template in hierarchy["templates"]}
    root_ids = {root["id"] for root in hierarchy["roots"]}
    if {"left_ear_template", "right_ear_template"} & template_ids:
        raise RuntimeError("Legacy tangent ear templates remain active.")
    if {"left_ear", "right_ear"} & root_ids:
        raise RuntimeError("Legacy tangent ear roots remain active.")
    print("legacy tangent plates removed", True, "OK")

    left = fields["left_ear__silhouette_mass"]
    right = fields["right_ear__silhouette_mass"]
    mirror_centers = (
        left["center"][0] == -right["center"][0]
        and left["center"][1:] == right["center"][1:]
    )
    mirror_radii = left["radii"] == right["radii"]
    if not mirror_centers or not mirror_radii:
        raise RuntimeError("Volumetric ears are not mirror-consistent.")
    print("volumetric mirror consistency", True, "OK")

    body = fields["body"]
    for label, ear in (("left", left), ("right", right)):
        width_radius, depth_radius, height_radius = ear["radii"]
        if depth_radius < 0.22 * min(2.0 * width_radius, 2.0 * height_radius):
            raise RuntimeError(f"{label} ear remains plate-like.")
        body_x = _body_cross_section_x(body, ear["center"])
        outer_x = abs(ear["center"][0]) + width_radius
        protrusion = outer_x - body_x
        if protrusion < 0.07 * semantic.body.width_mm:
            raise RuntimeError(f"{label} ear does not alter the silhouette enough.")
        center_value = sum(
            ((ear["center"][axis] - body["center"][axis]) / body["radii"][axis])
            ** 2
            for axis in range(3)
        )
        if center_value >= 1.0:
            raise RuntimeError(f"{label} ear lacks robust body intersection.")
    print("minimum ear volume", True, "OK")
    print("minimum silhouette protrusion", True, "OK")
    print("robust body intersection", True, "OK")

    specification = HierarchicalFeatureParser().parse_dict(motor)
    anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
    layout = HierarchicalFeatureVesselEngine.layout_report(specification)
    manufacturing = HierarchicalFeatureVesselEngine.feature_manufacturability_report(
        specification
    )
    if not all(anchors.values()):
        raise RuntimeError("Remaining surface anchors are invalid.")
    layout.validate()
    manufacturing.validate()
    print("remaining roots", len(specification.roots), "OK")
    print("remaining placements", len(HierarchicalFeatureVesselEngine.placements(specification)), "OK")
    print("anchor checks", len(anchors), "OK")
    print("layout checks", len(layout.checks), "OK")
    print("manufacturability checks", len(manufacturing.checks), "OK")
    print("-----------------------------------")
    print("No mesh generation or API credit required OK")
    print("DOBO Visual Acceptance Phases 4G-4K: Valid OK")


if __name__ == "__main__":
    main()
