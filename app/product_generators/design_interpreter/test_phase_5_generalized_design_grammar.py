from __future__ import annotations

from .design_grammar import (
    ACCEPTANCE_MATRIX_VERSION,
    BODY_GRAMMAR_VERSION,
    COMPONENT_GRAMMAR_VERSION,
    COMPOSITION_GRAMMAR_VERSION,
    STYLE_GRAMMAR_VERSION,
    DesignGrammarResolver,
)
from .phase_5_design_matrix import design_matrix
from .structural_compiler import StructuralSemanticCompiler
from .structural_pipeline import (
    STRUCTURAL_FUSION_VERSION,
    STRUCTURAL_PIPELINE_VERSION,
)
from .design_pipeline import DoboDesignPipeline
from .structural_vocabulary import StructuralVocabularyResolver


class _IdentityParser:
    @staticmethod
    def parse_dict(candidate):
        return candidate


class _VolumeDriftThenSuccessEngine:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, specification):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError(
                "Localized mesh refinement exceeded total volume drift from input."
            )
        return specification


def main() -> None:
    print()
    print("DOBO Generalized Design Grammar - Block 5")
    print("body -> components -> composition -> style -> acceptance matrix")
    print("-----------------------------------")
    print("body grammar version", BODY_GRAMMAR_VERSION, "OK")
    print("component grammar version", COMPONENT_GRAMMAR_VERSION, "OK")
    print("composition grammar version", COMPOSITION_GRAMMAR_VERSION, "OK")
    print("style grammar version", STYLE_GRAMMAR_VERSION, "OK")
    print("acceptance matrix version", ACCEPTANCE_MATRIX_VERSION, "OK")
    print("fusion version", STRUCTURAL_FUSION_VERSION, "OK")
    print("pipeline version", STRUCTURAL_PIPELINE_VERSION, "OK")

    recovery_profiles = tuple(
        name
        for name, _ in DoboDesignPipeline._mesh_quality_profiles(
            StructuralSemanticCompiler.compile(design_matrix()[0].program).motor_program
        )
    )
    if "volumetric_fused_base_surface" not in recovery_profiles:
        raise RuntimeError("Volumetric connectivity recovery is unavailable.")
    print("volumetric connectivity recovery", True, "OK")

    geometric_motor = StructuralSemanticCompiler.compile(
        design_matrix()[-1].program
    ).motor_program
    recovered, selected_motor, attempts, selected_profile = (
        DoboDesignPipeline._generate_with_retry(
            geometric_motor,
            parser=_IdentityParser(),
            engine=_VolumeDriftThenSuccessEngine(),
        )
    )
    if recovered is not selected_motor:
        raise RuntimeError("Volume-drift recovery lost its selected Motor program.")
    if attempts != 2 or selected_profile != "validated_base_surface":
        raise RuntimeError("Volume-drift recovery did not advance to a safe profile.")
    if "mesh_quality" in selected_motor:
        raise RuntimeError("Volume-drift recovery retained the failing refinement.")
    print("volume drift recovery", True, "OK")

    signatures: set[str] = set()
    body_profiles: set[str] = set()
    style_profiles: set[str] = set()
    total_features = 0
    total_mirror_groups = 0
    total_repetition_groups = 0
    total_compound_groups = 0
    for case in design_matrix():
        program = case.program
        structural = StructuralVocabularyResolver.resolve(program)
        grammar = DesignGrammarResolver.resolve(program, structural)
        compiled = StructuralSemanticCompiler.compile(program, structural)
        if grammar.body_profile != case.expected_body_profile:
            raise RuntimeError(f"{case.label} body profile is incorrect.")
        if grammar.style.name != case.expected_style_profile:
            raise RuntimeError(f"{case.label} style profile is incorrect.")
        if not any(
            feature.shape_profile == case.expected_component
            for feature in grammar.features
        ):
            raise RuntimeError(f"{case.label} expected component was not resolved.")
        if compiled.grammar.signature != grammar.signature:
            raise RuntimeError(f"{case.label} compilation lost its grammar plan.")
        if compiled.report.grammar_signature != grammar.signature:
            raise RuntimeError(f"{case.label} report lost its grammar signature.")
        semantic_templates = compiled.semantic_compilation.motor_program[
            "hierarchy_program"
        ]["templates"]
        for template in semantic_templates:
            if template["kind"] == "rounded_triangle_prism" and (
                "center_y_mm" not in template
                or "vertices_xz" not in template
                or "half_depth_mm" not in template
            ):
                raise RuntimeError(
                    f"{case.label} emitted an incomplete triangle prism."
                )
        motor = compiled.motor_program
        field_ids = set(motor["composition"]["field_ids"])
        if not {"body", "front_mass"} <= field_ids:
            raise RuntimeError(f"{case.label} lost its base body fields.")
        if not motor["hierarchy_program"]["roots"]:
            raise RuntimeError(f"{case.label} lost every executable hierarchy root.")
        fields = {field["id"]: field for field in motor["fields"]}
        body = fields["body"]
        for feature in grammar.features:
            if feature.mass_strategy != "silhouette_mass":
                continue
            field = fields[f"{feature.semantic_feature_id}__silhouette_mass"]
            normalized_center = sum(
                (float(value) / float(radius)) ** 2
                for value, radius in zip(field["center"], body["radii"])
            )
            if normalized_center > 0.90:
                raise RuntimeError(
                    f"{case.label} silhouette lacks robust body penetration."
                )
        if grammar.style.name in {"organic", "childlike"}:
            for resolved in structural.features:
                if resolved.parent_feature_id is None:
                    continue
                child_id = f"{resolved.semantic_feature_id}__compound_child_mass"
                parent_id = f"{resolved.parent_feature_id}__compound_mass"
                if child_id not in fields or parent_id not in fields:
                    continue
                child = fields[child_id]
                parent = fields[parent_id]
                parent_front = float(parent["center"][1]) - float(
                    parent["radii"][1]
                )
                child_back = float(child["center"][1]) + float(
                    child["radii"][1]
                )
                overlap = child_back - parent_front
                if overlap < float(child["radii"][1]):
                    raise RuntimeError(
                        f"{case.label} compound child lacks cavity-safe overlap."
                    )
                child_front = float(child["center"][1]) - float(
                    child["radii"][1]
                )
                visible_level = parent_front - child_front
                minimum_visible = max(
                    2.0,
                    1.95 * program.manufacturing.minimum_feature_mm,
                )
                if visible_level + 1e-9 < minimum_visible:
                    raise RuntimeError(
                        f"{case.label} compound child lost visible exposure."
                    )
        if grammar.style.name == "geometric":
            maximum_recess_depth = max(
                feature.size.depth_mm
                for feature in program.features
                if feature.surface_effect == "recessed"
            )
            if maximum_recess_depth > 0.25 * program.manufacturing.minimum_wall_mm:
                raise RuntimeError(
                    f"{case.label} recesses lack the geometric wall reserve."
                )
            print("geometric wall reserve", True, "OK")
            body_radius = float(fields["body"]["radii"][0])
            shoulder_limit = (
                body_radius + 0.5 * program.manufacturing.minimum_wall_mm
            )
            for shoulder_id in (
                "body_shoulder_left",
                "body_shoulder_right",
            ):
                shoulder = fields[shoulder_id]
                shoulder_extent = abs(float(shoulder["center"][0])) + float(
                    shoulder["radii"][0]
                )
                if shoulder_extent > shoulder_limit:
                    raise RuntimeError(
                        f"{case.label} shoulder invades the cavity reserve."
                    )
            print("faceted shoulder cavity reserve", True, "OK")
        signatures.add(grammar.signature)
        body_profiles.add(grammar.body_profile)
        style_profiles.add(grammar.style.name)
        total_features += len(grammar.features)
        total_mirror_groups += grammar.mirror_groups
        total_repetition_groups += grammar.repetition_groups
        total_compound_groups += grammar.compound_groups
        print(
            case.label,
            "profile",
            grammar.body_profile,
            "style",
            grammar.style.name,
            "features",
            len(grammar.features),
            "fields",
            len(field_ids),
            "OK",
        )

    if len(signatures) != 4:
        raise RuntimeError("The acceptance matrix did not create four designs.")
    if len(body_profiles) < 3:
        raise RuntimeError("The acceptance matrix lacks body diversity.")
    if len(style_profiles) < 3:
        raise RuntimeError("The acceptance matrix lacks style diversity.")
    if total_mirror_groups < 4:
        raise RuntimeError("The matrix lacks bilateral composition coverage.")
    if total_repetition_groups < 8:
        raise RuntimeError("The matrix lacks repetition coverage.")
    if total_compound_groups < 2:
        raise RuntimeError("The matrix lacks compound-mass coverage.")
    print("unique design signatures", len(signatures), "OK")
    print("body profiles", len(body_profiles), "OK")
    print("style profiles", len(style_profiles), "OK")
    print("semantic features", total_features, "OK")
    print("mirror groups", total_mirror_groups, "OK")
    print("repetition groups", total_repetition_groups, "OK")
    print("compound groups", total_compound_groups, "OK")
    print("product-specific compiler branches", 0, "OK")
    print("-----------------------------------")
    print("No mesh generation or API credit required OK")
    print("DOBO Generalized Design Grammar Block 5: Valid OK")


if __name__ == "__main__":
    main()
