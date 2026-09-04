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
    COMPOUND_MASS_VERSION,
    EAR_CALIBRATION_VERSION,
    FACIAL_ACCEPTANCE_VERSION,
    LOCAL_FUSION_VERSION,
    VISUAL_GRID_VERSION,
    StructuralSemanticCompiler,
)
from .structural_pipeline import (
    STRUCTURAL_FUSION_VERSION,
    STRUCTURAL_PIPELINE_VERSION,
)


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")


def main() -> None:
    print()
    print("DOBO Facial Volume - Phases 4L-4P")
    print("round ears -> compound mass -> local fusion -> acceptance -> pipeline")
    print("-----------------------------------")
    semantic = SemanticProgramParser().parse_dict(
        json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    )
    compiled = StructuralSemanticCompiler.compile(semantic)
    motor = compiled.motor_program
    hierarchy = motor["hierarchy_program"]
    fields = {field["id"]: field for field in motor["fields"]}
    roots = {root["id"]: root for root in hierarchy["roots"]}
    templates = {template["id"] for template in hierarchy["templates"]}

    print("ear calibration version", EAR_CALIBRATION_VERSION, "OK")
    print("compound mass version", COMPOUND_MASS_VERSION, "OK")
    print("local fusion version", LOCAL_FUSION_VERSION, "OK")
    print("facial acceptance version", FACIAL_ACCEPTANCE_VERSION, "OK")
    print("visual grid version", VISUAL_GRID_VERSION, "OK")
    print("fusion version", STRUCTURAL_FUSION_VERSION, "OK")
    print("pipeline version", STRUCTURAL_PIPELINE_VERSION, "OK")

    if compiled.report.volumetric_silhouette_features != 2:
        raise RuntimeError("Expected two calibrated volumetric ears.")
    if compiled.report.volumetric_compound_parents != 1:
        raise RuntimeError("Expected one volumetric compound parent.")
    print("calibrated volumetric ears", 2, "OK")
    print("volumetric compound parents", 1, "OK")

    for ear_id in (
        "left_ear__silhouette_mass",
        "right_ear__silhouette_mass",
    ):
        ear = fields[ear_id]
        planar_min = min(ear["radii"][0], ear["radii"][2])
        if ear["radii"][1] < 0.62 * planar_min:
            raise RuntimeError(f"{ear_id} is not round enough in profile.")
        if abs(ear["center"][0]) < 0.37 * semantic.body.width_mm:
            raise RuntimeError(f"{ear_id} remains too absorbed by the body.")
        if ear["center"][2] + ear["radii"][2] >= 0.39 * semantic.body.height_mm:
            raise RuntimeError(f"{ear_id} remains too close to the opening.")
    print("round ear profile", True, "OK")
    print("ear lateral exposure", True, "OK")
    print("ear opening separation", True, "OK")

    muzzle = fields["muzzle__compound_mass"]
    if "muzzle" in roots or "muzzle_template" in templates:
        raise RuntimeError("Legacy surface muzzle remains active.")
    if muzzle["radii"][1] < 0.14 * min(
        2.0 * muzzle["radii"][0],
        2.0 * muzzle["radii"][2],
    ):
        raise RuntimeError("Muzzle remains plate-like.")
    print("legacy muzzle plate removed", True, "OK")
    print("volumetric muzzle depth", True, "OK")

    nose = fields.get("nose__compound_child_mass")
    if nose is None:
        raise RuntimeError("Nose was not promoted with the muzzle compound.")
    if "nose" in roots or "nose_template" in templates:
        raise RuntimeError("Legacy surface nose remains active.")
    print("nose promoted with compound mass", True, "OK")

    blend = float(motor["composition"]["blend_mm"])
    if not 2.5 <= blend <= 4.0:
        raise RuntimeError("Body-field fusion is outside the calibrated range.")
    print("calibrated field fusion mm", round(blend, 4), "OK")
    original_front = (
        -0.5 * semantic.body.depth_mm
        - max(
            8.0,
            0.08
            * max(
                semantic.body.width_mm,
                semantic.body.depth_mm,
                semantic.body.height_mm,
            ),
        )
    )
    if float(motor["grid"]["minimum"][1]) > original_front - 6.0:
        raise RuntimeError("Promoted facial masses lack front grid reserve.")
    print("promoted mass grid reserve mm", 6.0, "OK")

    specification = HierarchicalFeatureParser().parse_dict(motor)
    anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
    layout = HierarchicalFeatureVesselEngine.layout_report(specification)
    manufacturing = HierarchicalFeatureVesselEngine.feature_manufacturability_report(
        specification
    )
    if not all(anchors.values()):
        raise RuntimeError("Facial-volume surface anchors are invalid.")
    layout.validate()
    manufacturing.validate()
    print("remaining roots", len(specification.roots), "OK")
    print(
        "remaining placements",
        len(HierarchicalFeatureVesselEngine.placements(specification)),
        "OK",
    )
    print("anchor checks", len(anchors), "OK")
    print("layout checks", len(layout.checks), "OK")
    print("manufacturability checks", len(manufacturing.checks), "OK")
    print("-----------------------------------")
    print("No mesh generation or API credit required OK")
    print("DOBO Facial Volume Phases 4L-4P: Valid OK")


if __name__ == "__main__":
    main()
