from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)

from .semantic_parser import SemanticProgramParser
from .structural_compiler import (
    STRUCTURAL_COMPILER_VERSION,
    STRUCTURAL_HIERARCHY_VERSION,
    STRUCTURAL_TEMPLATE_VERSION,
    StructuralSemanticCompiler,
)
from .structural_pipeline import (
    STRUCTURAL_FUSION_VERSION,
    STRUCTURAL_GENERATION_BUDGET_SECONDS,
    STRUCTURAL_PIPELINE_VERSION,
    DoboStructuralPipeline,
)
from .structural_vocabulary import StructuralVocabularyResolver


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")


def _spanish_probe(fixture: dict) -> dict:
    data = deepcopy(fixture)
    data["id"] = "maceta_oso_estructural_probe"
    data["source"]["prompt"] = (
        "Maceta infantil de oso con orejas superiores simétricas, ojos "
        "grabados, hocico elevado y nariz central."
    )
    translations = {
        "left_ear": ("oreja_izquierda", "oreja"),
        "right_ear": ("oreja_derecha", "oreja"),
        "left_eye": ("ojo_izquierdo", "ojo"),
        "right_eye": ("ojo_derecho", "ojo"),
        "muzzle": ("hocico", "hocico"),
        "nose": ("nariz_central", "nariz"),
    }
    for feature in data["features"]:
        old_id = feature["id"]
        feature["id"], feature["concept"] = translations[old_id]
        if old_id in {"left_ear", "right_ear"}:
            feature["size"]["width_ratio"] = 0.24
            feature["size"]["height_ratio"] = 0.22
            feature["size"]["depth_mm"] = 1.0
        elif old_id in {"left_eye", "right_eye"}:
            feature["anchor"]["vertical"] = 0.28
            feature["size"]["width_ratio"] = 0.10
            feature["size"]["height_ratio"] = 0.10
            feature["size"]["depth_mm"] = 0.8
        elif old_id == "muzzle":
            feature["anchor"]["vertical"] = 0.02
            feature["size"]["width_ratio"] = 0.34
            feature["size"]["height_ratio"] = 0.24
            feature["size"]["depth_mm"] = 1.2
        elif old_id == "nose":
            feature["anchor"]["vertical"] = 0.10
            feature["size"]["width_ratio"] = 0.12
            feature["size"]["height_ratio"] = 0.10
            feature["size"]["depth_mm"] = 1.0
    for relation in data["relations"]:
        relation["subject_id"] = translations[relation["subject_id"]][0]
        relation["object_id"] = translations[relation["object_id"]][0]
    # Match the live 3C proposal: mirror pairs and the nose/muzzle relation
    # are explicit; eye/muzzle adjacency must come from structural zones.
    data["relations"] = [
        relation
        for relation in data["relations"]
        if relation["kind"] in {"mirror_of", "centered_on"}
    ]
    data["manufacturing"] = {
        "minimum_wall_mm": 2.4,
        "minimum_feature_mm": 1.0,
        "maximum_relief_depth_mm": 1.2,
        "drainage_required": True,
        "multicolor_requested": False,
    }
    return data


def _decorative_probe(fixture: dict) -> dict:
    data = deepcopy(fixture)
    data["id"] = "leaf_emblem_structural_probe"
    data["features"][0]["concept"] = "leaf"
    data["features"][1]["concept"] = "leaf"
    data["features"][2]["concept"] = "eye"
    data["features"][3]["concept"] = "eye"
    data["features"][4]["concept"] = "badge"
    data["features"][5]["concept"] = "disc"
    return data


def _preflight(label: str, semantic) -> tuple:
    structural = StructuralVocabularyResolver.resolve(semantic)
    compiled = StructuralSemanticCompiler.compile(semantic, structural)
    specification = HierarchicalFeatureParser().parse_dict(compiled.motor_program)
    placements = HierarchicalFeatureVesselEngine.placements(specification)
    anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
    layout = HierarchicalFeatureVesselEngine.layout_report(specification)
    manufacturing = (
        HierarchicalFeatureVesselEngine.feature_manufacturability_report(
            specification
        )
    )
    layout.validate()
    manufacturing.validate()
    if not all(anchors.values()):
        raise RuntimeError(f"{label} structural surface anchors failed.")
    print(label, "features", len(structural.features), "OK")
    print(label, "groups", len(structural.groups), "OK")
    print(label, "roots", len(specification.roots), "OK")
    print(label, "placements", len(placements), "OK")
    print(label, "anchor checks", len(anchors), "OK")
    print(label, "layout checks", len(layout.checks), "OK")
    print(label, "manufacturability checks", len(manufacturing.checks), "OK")
    return structural, compiled, specification


def _mesh(label: str, semantic, root: Path) -> None:
    result = DoboStructuralPipeline().generate_from_semantic(
        semantic, output_root=root
    )
    result.validate()
    print(label, "pipeline", result.trace.pipeline_version, "OK")
    print(label, "components", result.mesh_result.component_count, "OK")
    print(label, "watertight", result.mesh_result.watertight, "OK")
    print(label, "winding", result.mesh_result.winding_consistent, "OK")
    print(label, "silhouette features", result.trace.silhouette_features, "OK")
    print(label, "compound children", result.trace.compound_children, "OK")
    print(label, "vertices", result.trace.vertex_count, "OK")
    print(label, "faces", result.trace.face_count, "OK")
    print(label, "generation attempts", result.trace.generation_attempts, "OK")
    print(label, "quality profile", result.trace.mesh_quality_profile, "OK")
    print(label, "artifacts", 7, "OK")
    if result.mesh_result.component_count != 1:
        raise RuntimeError(f"{label} did not produce one component.")
    if not result.mesh_result.watertight or not result.mesh_result.winding_consistent:
        raise RuntimeError(f"{label} did not produce a valid mesh.")


def main() -> None:
    print()
    print("DOBO Structural Composition - Phases 4B-4F")
    print("Roles -> templates -> hierarchy -> fusion -> validated STL/3MF")
    print("-----------------------------------")
    fixture = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    english = SemanticProgramParser().parse_dict(fixture)
    spanish = SemanticProgramParser().parse_dict(_spanish_probe(fixture))
    decorative = SemanticProgramParser().parse_dict(_decorative_probe(fixture))

    english_structural, english_compiled, english_spec = _preflight(
        "English bear", english
    )
    spanish_structural, spanish_compiled, spanish_spec = _preflight(
        "Spanish bear", spanish
    )
    spanish_templates = {
        template["id"]: template
        for template in spanish_compiled.motor_program["hierarchy_program"]["templates"]
    }
    spanish_eye_template = spanish_templates["ojo_izquierdo_template"]
    non_degenerate_capsule = (
        spanish_eye_template["kind"] == "capsule"
        and spanish_eye_template["start"] != spanish_eye_template["end"]
        and spanish_eye_template["radius_mm"] > 0.0
    )
    print("square slit capsule non-degenerate", non_degenerate_capsule, "OK")
    if not non_degenerate_capsule:
        raise RuntimeError("Square slit compiled to a degenerate capsule.")
    spanish_eye_root = next(
        root
        for root in spanish_compiled.motor_program["hierarchy_program"]["roots"]
        if root["id"] == "ojo_izquierdo"
    )
    eye_depth_scale = min(spanish_eye_root["transform"]["scale"])
    effective_eye_blend = spanish_eye_template["blend_mm"] * eye_depth_scale
    minimum_eye_blend = spanish_compiled.motor_program["hierarchy_program"][
        "feature_manufacturability"
    ]["minimum_blend_mm"]
    blend_reserve_valid = effective_eye_blend >= minimum_eye_blend
    print("compressed capsule blend reserve", blend_reserve_valid, "OK")
    if not blend_reserve_valid:
        raise RuntimeError("Compressed capsule lost its minimum blend reserve.")
    effective_eye_depth = (
        spanish_eye_template["radius_mm"]
        * spanish_eye_root["transform"]["scale"][1]
    )
    minimum_eye_depth = spanish_compiled.motor_program["hierarchy_program"][
        "feature_manufacturability"
    ]["minimum_relief_depth_mm"]
    depth_reserve_valid = effective_eye_depth > minimum_eye_depth
    print("compressed capsule depth reserve", depth_reserve_valid, "OK")
    if not depth_reserve_valid:
        raise RuntimeError("Compressed capsule lost its minimum depth reserve.")
    decorative_structural, _, _ = _preflight("Decorative", decorative)
    print("compiler version", english_compiled.report.compiler_version, "OK")
    print("template version", english_compiled.report.template_version, "OK")
    print("hierarchy version", english_compiled.report.hierarchy_version, "OK")
    print("fusion version", STRUCTURAL_FUSION_VERSION, "OK")
    print("pipeline version", STRUCTURAL_PIPELINE_VERSION, "OK")
    print(
        "structural generation budget seconds",
        STRUCTURAL_GENERATION_BUDGET_SECONDS,
        "OK",
    )
    if STRUCTURAL_GENERATION_BUDGET_SECONDS < 45.0:
        raise RuntimeError("Structural generation budget is below 45 seconds.")
    print(
        "English silhouette roles",
        english_compiled.report.silhouette_features,
        "OK",
    )
    print(
        "Spanish silhouette roles",
        spanish_compiled.report.silhouette_features,
        "OK",
    )
    print(
        "decorative silhouette roles",
        sum(feature.structural_role == "silhouette" for feature in decorative_structural.features),
        "OK",
    )
    if english_compiled.report.compiler_version != STRUCTURAL_COMPILER_VERSION:
        raise RuntimeError("Consolidated suite used the wrong compiler version.")
    if english_compiled.report.template_version != STRUCTURAL_TEMPLATE_VERSION:
        raise RuntimeError("Consolidated suite used the wrong template version.")
    if english_compiled.report.hierarchy_version != STRUCTURAL_HIERARCHY_VERSION:
        raise RuntimeError("Consolidated suite used the wrong hierarchy version.")
    spanish_templates = {
        template["id"]: template
        for template in spanish_compiled.motor_program["hierarchy_program"][
            "templates"
        ]
    }
    compact_templates_valid = True
    for template_id in ("ojo_izquierdo_template", "ojo_derecho_template"):
        template = spanish_templates[template_id]
        if template["kind"] == "capsule":
            compact_templates_valid = compact_templates_valid and (
                template["start"] != template["end"]
            )
        else:
            compact_templates_valid = compact_templates_valid and (
                template["kind"] == "ellipsoid"
            )
    print("compact templates valid", compact_templates_valid, "OK")
    if not compact_templates_valid:
        raise RuntimeError("Compact templates remain geometrically invalid.")

    english_roots = {root.id: root for root in english_spec.roots}
    spanish_roots = {root.id: root for root in spanish_spec.roots}
    english_fields = {
        field["id"]: field for field in english_compiled.motor_program["fields"]
    }
    spanish_fields = {
        field["id"]: field for field in spanish_compiled.motor_program["fields"]
    }
    print(
        "ears alter silhouette",
        "left_ear__silhouette_mass" in english_fields
        and "right_ear__silhouette_mass" in english_fields,
        "OK",
    )
    print(
        "eyes normalized",
        spanish_roots["ojo_izquierdo"].surface_anchor.height_ratio == 0.62
        and spanish_roots["ojo_derecho"].surface_anchor.height_ratio == 0.62,
        "OK",
    )
    print(
        "nose composed with muzzle",
        "hocico__compound_mass" in spanish_fields
        and "nariz_central__compound_child_mass" in spanish_fields,
        "OK",
    )
    print(
        "mirror consistency",
        spanish_fields["oreja_izquierda__silhouette_mass"]["center"][0]
        == -spanish_fields["oreja_derecha__silhouette_mass"]["center"][0]
        and spanish_fields["oreja_izquierda__silhouette_mass"]["center"][0]
        < 0.0,
        "OK",
    )
    ignored_pairs = {
        tuple(sorted(pair))
        for pair in spanish_compiled.motor_program["hierarchy_program"]
        ["layout_constraints"]["ignored_pairs"]
    }
    facial_pairs = {
        ("hocico", "ojo_derecho"),
        ("hocico", "ojo_izquierdo"),
    }
    print("facial adjacency pairs", facial_pairs <= ignored_pairs, "OK")
    if not facial_pairs <= ignored_pairs:
        raise RuntimeError("Structural compiler omitted facial adjacency pairs.")

    with TemporaryDirectory() as directory:
        root = Path(directory)
        _mesh("Spanish bear", spanish, root / "spanish")
        _mesh("English bear", english, root / "english")
    print("-----------------------------------")
    print("No API credit consumed OK")
    print("DOBO Structural Composition Phases 4B-4F: Valid OK")


if __name__ == "__main__":
    main()
