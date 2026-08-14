from __future__ import annotations

import json
from pathlib import Path

from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)

from .semantic_parser import SemanticProgramParser
from .structural_compiler import (
    CANONICAL_FUSION_VERSION,
    MUZZLE_EXPOSURE_VERSION,
    NOSE_MASS_VERSION,
    SURFACE_ACCEPTANCE_VERSION,
    StructuralSemanticCompiler,
)
from .structural_pipeline import (
    STRUCTURAL_FUSION_VERSION,
    STRUCTURAL_PIPELINE_VERSION,
)
from .structural_morphogenesis import front_surface_y


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")


def _front_extent(field: dict) -> float:
    return abs(float(field["center"][1]) - float(field["radii"][1]))


def main() -> None:
    print()
    print("DOBO Canonical Face - Phases 4Q-4U")
    print("muzzle exposure -> nose mass -> canonical fusion -> surface -> pipeline")
    print("-----------------------------------")
    semantic = SemanticProgramParser().parse_dict(
        json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    )
    compiled = StructuralSemanticCompiler.compile(semantic)
    motor = compiled.motor_program
    hierarchy = motor["hierarchy_program"]
    fields = {field["id"]: field for field in motor["fields"]}
    roots = {root["id"]: root for root in hierarchy["roots"]}
    templates = {template["id"]: template for template in hierarchy["templates"]}

    print("muzzle exposure version", MUZZLE_EXPOSURE_VERSION, "OK")
    print("nose mass version", NOSE_MASS_VERSION, "OK")
    print("canonical fusion version", CANONICAL_FUSION_VERSION, "OK")
    print("surface acceptance version", SURFACE_ACCEPTANCE_VERSION, "OK")
    print("fusion version", STRUCTURAL_FUSION_VERSION, "OK")
    print("pipeline version", STRUCTURAL_PIPELINE_VERSION, "OK")

    if compiled.report.volumetric_compound_parents != 1:
        raise RuntimeError("Expected one volumetric muzzle parent.")
    if compiled.report.volumetric_compound_children != 1:
        raise RuntimeError("Expected one volumetric nose child.")
    print("volumetric muzzle parents", 1, "OK")
    print("volumetric nose children", 1, "OK")

    muzzle = fields["muzzle__compound_mass"]
    nose = fields["nose__compound_child_mass"]
    body_front = -front_surface_y(
        motor,
        x=float(muzzle["center"][0]),
        z=float(muzzle["center"][2]),
    )
    muzzle_front = _front_extent(muzzle)
    nose_front = _front_extent(nose)
    nose_back = abs(float(nose["center"][1]) + float(nose["radii"][1]))
    if muzzle_front - body_front < 5.0:
        raise RuntimeError("Muzzle is not sufficiently exposed from the body.")
    if nose_front - muzzle_front < 2.0:
        raise RuntimeError("Nose lacks a readable second facial level.")
    if nose_back > muzzle_front:
        raise RuntimeError("Nose does not overlap the muzzle mass.")
    print("muzzle exposure mm", round(muzzle_front - body_front, 4), "OK")
    print("nose second level mm", round(nose_front - muzzle_front, 4), "OK")
    print("nose muzzle overlap", True, "OK")

    legacy_ids = {"muzzle", "nose"}
    if legacy_ids & set(roots):
        raise RuntimeError("Legacy additive facial roots remain active.")
    if {"muzzle_template", "nose_template"} & set(templates):
        raise RuntimeError("Legacy additive facial templates remain active.")
    add_templates = [
        template["id"]
        for template in templates.values()
        if template["operation"] == "add"
    ]
    if add_templates:
        raise RuntimeError(f"Independent additive templates remain: {add_templates}")
    print("independent additive roots removed", True, "OK")
    print("canonical connectivity proxy", True, "OK")

    blend = float(motor["composition"]["blend_mm"])
    if not 3.5 <= blend <= 4.0:
        raise RuntimeError("Calibrated canonical fusion is outside its range.")
    print("canonical field fusion mm", round(blend, 4), "OK")

    left = fields["left_ear__silhouette_mass"]
    right = fields["right_ear__silhouette_mass"]
    if left["radii"] != right["radii"] or left["center"][0] != -right["center"][0]:
        raise RuntimeError("Ear mass symmetry was lost.")
    print("ear mass symmetry", True, "OK")

    specification = HierarchicalFeatureParser().parse_dict(motor)
    anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
    layout = HierarchicalFeatureVesselEngine.layout_report(specification)
    manufacturing = HierarchicalFeatureVesselEngine.feature_manufacturability_report(
        specification
    )
    if not all(anchors.values()):
        raise RuntimeError("Canonical facial anchors are invalid.")
    layout.validate()
    manufacturing.validate()
    placements = HierarchicalFeatureVesselEngine.placements(specification)
    print("remaining roots", len(specification.roots), "OK")
    print("remaining subtractive placements", len(placements), "OK")
    print("anchor checks", len(anchors), "OK")
    print("layout checks", len(layout.checks), "OK")
    print("manufacturability checks", len(manufacturing.checks), "OK")
    print("-----------------------------------")
    print("No mesh generation or API credit required OK")
    print("DOBO Canonical Face Phases 4Q-4U: Valid OK")


if __name__ == "__main__":
    main()
