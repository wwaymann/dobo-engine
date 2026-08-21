from __future__ import annotations

from tempfile import TemporaryDirectory
from zipfile import ZipFile

import trimesh

from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)
from product_generators.organic_shapes.engine import OrganicShapeEngine

from .complex_composition import (
    COMPLEX_ACCEPTANCE_VERSION,
    COMPLEX_TOPOLOGY_VERSION,
    MULTILEVEL_HIERARCHY_VERSION,
    NEGATIVE_VOLUME_VERSION,
    STRUCTURAL_SPAN_VERSION,
    VISUAL_INTEGRATION_VERSION,
)
from .intelligent_surfaces import (
    ADAPTIVE_MAPPING_VERSION,
    COLOR_ZONE_VERSION,
    IntelligentSurfaceCompiler,
    RELIEF_SYNTHESIS_VERSION,
    SURFACE_ACCEPTANCE_VERSION,
    SURFACE_INTENT_VERSION,
)
from .phase_7_8_macroblock_matrix import macroblock_a_matrix
from .structural_compiler import StructuralSemanticCompiler
from .three_mf_export import ThreeMFMeshExporter


def _check(label: str, actual, expected) -> None:
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected!r}, got {actual!r}.")
    print(label, actual, "OK")


def main() -> None:
    print()
    print("DOBO Macroblock A - Blocks 7-8")
    print("complex composition -> intelligent surfaces -> multicolor 3MF")
    print("-----------------------------------")
    _check("complex topology version", COMPLEX_TOPOLOGY_VERSION, "7A.1")
    _check("structural span version", STRUCTURAL_SPAN_VERSION, "7B.1")
    _check("negative volume version", NEGATIVE_VOLUME_VERSION, "7C.1")
    _check("multilevel hierarchy version", MULTILEVEL_HIERARCHY_VERSION, "7D.1")
    _check("complex acceptance version", COMPLEX_ACCEPTANCE_VERSION, "7E.1")
    _check("visual integration version", VISUAL_INTEGRATION_VERSION, "7E.2")
    _check("surface intent version", SURFACE_INTENT_VERSION, "8A.1")
    _check("adaptive mapping version", ADAPTIVE_MAPPING_VERSION, "8B.1")
    _check("relief synthesis version", RELIEF_SYNTHESIS_VERSION, "8C.1")
    _check("color zone version", COLOR_ZONE_VERSION, "8D.1")
    _check("surface acceptance version", SURFACE_ACCEPTANCE_VERSION, "8E.1")

    profiles: set[str] = set()
    mappings: set[str] = set()
    for case in macroblock_a_matrix():
        compilation = StructuralSemanticCompiler.compile(case.program)
        report = compilation.report
        _check(f"{case.label} profile", report.complex_profile, case.expected_profile)
        if report.hierarchy_depth < case.minimum_depth:
            raise RuntimeError(f"{case.label} lost multilevel hierarchy.")
        specification = HierarchicalFeatureParser().parse_dict(
            compilation.motor_program
        )
        if case.expected_profile == "spanning_frame":
            roots = {
                root["id"]: root
                for root in compilation.motor_program["hierarchy_program"]["roots"]
            }
            span_ids = {
                feature.id
                for feature in case.program.features
                if feature.concept in {"handle", "bridge"}
                and feature.surface_effect == "raised"
            }
            connector_templates = [
                template
                for template in compilation.motor_program["hierarchy_program"]
                ["templates"]
                if template["id"].endswith("_fusion_foot_template")
            ]
            _check("span fusion feet", len(connector_templates), 2 * len(span_ids))
            if any(len(roots[feature_id]["template_ids"]) < 3 for feature_id in span_ids):
                raise RuntimeError("A structural span lost its lateral fusion feet.")
            structural_depth = set(
                compilation.motor_program["hierarchy_program"]
                ["feature_manufacturability"]
                ["structural_depth_feature_ids"]
            )
            if not span_ids.issubset(structural_depth):
                raise RuntimeError("Structural span depth classification was lost.")
        anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(
            specification
        )
        layout = HierarchicalFeatureVesselEngine.layout_report(specification)
        manufacturing = (
            HierarchicalFeatureVesselEngine.feature_manufacturability_report(
                specification
            )
        )
        if not all(anchors.values()):
            raise RuntimeError(f"{case.label} anchor checks failed.")
        layout.validate()
        manufacturing.validate()
        surface, surface_report = IntelligentSurfaceCompiler.compile(
            case.program,
            compilation.motor_program,
            case.surfaces,
        )
        surface.validate()
        surface_report.validate(len(case.surfaces))
        kinds = {layer.kind for layer in surface.layers}
        if kinds != {"text", "svg", "image", "procedural_relief"}:
            raise RuntimeError(f"{case.label} lost surface media kinds.")
        if surface_report.color_zones != 5:
            raise RuntimeError(f"{case.label} lost multicolor zones.")
        profiles.add(report.complex_profile)
        mappings.update(surface_report.mapping_modes)
        print(
            case.label,
            "nodes",
            report.complex_nodes,
            "edges",
            report.complex_edges,
            "depth",
            report.hierarchy_depth,
            "negative",
            report.negative_volumes,
            "surfaces",
            surface_report.layer_count,
            "colors",
            surface_report.color_zones,
            "OK",
        )

    _check("unique complex profiles", len(profiles), 3)
    if len(mappings) < 3:
        raise RuntimeError("Macroblock A did not exercise adaptive surface mapping.")
    print("adaptive surface mapping modes", len(mappings), "OK")

    primary = trimesh.creation.icosphere(subdivisions=2, radius=10.0)
    residue = trimesh.creation.icosphere(subdivisions=0, radius=0.05)
    residue.apply_translation([14.0, 0.0, 0.0])
    cleaned = OrganicShapeEngine._remove_numerical_islands(
        trimesh.util.concatenate([primary, residue]),
        0.72,
    )
    _check(
        "sub-voxel island cleanup",
        len(tuple(cleaned.split(only_watertight=False))),
        1,
    )

    with TemporaryDirectory() as directory:
        case = macroblock_a_matrix()[0]
        compilation = StructuralSemanticCompiler.compile(case.program)
        surface, _ = IntelligentSurfaceCompiler.compile(
            case.program, compilation.motor_program, case.surfaces
        )
        mesh = trimesh.creation.icosphere(subdivisions=2, radius=30.0)
        result = ThreeMFMeshExporter.export(
            mesh,
            f"{directory}/macroblock_a_surface.3mf",
            name="macroblock_a_surface",
            surface_program=surface,
        )
        result.validate()
        with ZipFile(result.path, "r") as package:
            model = package.read("3D/3dmodel.model").decode("utf-8")
        if "<basematerials" not in model or 'pid="2"' not in model:
            raise RuntimeError("3MF surface material properties were not exported.")
        if result.material_count != 5 or result.painted_triangle_count <= 0:
            raise RuntimeError("3MF surface color zones were not assigned.")
        print("3MF material zones", result.material_count, "OK")
        print("3MF painted triangles", result.painted_triangle_count, "OK")

    print("-----------------------------------")
    print("No mesh production or API credit required OK")
    print("DOBO Macroblock A Blocks 7-8: Valid OK")


if __name__ == "__main__":
    main()
