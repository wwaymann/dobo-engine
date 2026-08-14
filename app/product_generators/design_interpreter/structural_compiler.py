from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import cos, radians, sin
from typing import Any

from .design_grammar import (
    DesignGrammarPlan,
    DesignGrammarResolver,
    GrammarFeaturePlan,
)
from .semantic_compiler import SemanticCompilationResult, SemanticToMotorCompiler
from .semantic_contract import DesignSemanticProgram
from .structural_vocabulary import (
    StructuralDesignProgram,
    StructuralFeature,
    StructuralVocabularyResolver,
)
from .structural_morphogenesis import (
    MORPHOLOGY_ACCEPTANCE_VERSION,
    SECTION_PROFILE_VERSION,
    STRUCTURAL_SYNTHESIS_VERSION,
    TOPOLOGY_GRAPH_VERSION,
    StructuralBodySynthesizer,
    StructuralMorphogenesisResolver,
    front_surface_y,
)


STRUCTURAL_COMPILER_VERSION = "4B.1"
STRUCTURAL_TEMPLATE_VERSION = "4C.1"
STRUCTURAL_HIERARCHY_VERSION = "4D.1"
STRUCTURAL_ORIENTATION_VERSION = "4G.1"
VOLUMETRIC_SILHOUETTE_VERSION = "4H.1"
SILHOUETTE_VALIDATION_VERSION = "4J.1"
EAR_CALIBRATION_VERSION = "4L.1"
COMPOUND_MASS_VERSION = "4M.1"
LOCAL_FUSION_VERSION = "4N.1"
FACIAL_ACCEPTANCE_VERSION = "4O.1"
VISUAL_GRID_VERSION = "4O.2"
MUZZLE_EXPOSURE_VERSION = "4Q.1"
NOSE_MASS_VERSION = "4R.1"
CANONICAL_FUSION_VERSION = "4S.1"
SURFACE_ACCEPTANCE_VERSION = "4T.1"
ADVANCED_PRIMITIVE_VERSION = "6A.1"
CLEAN_COMPOSITION_VERSION = "6B.2"
STYLE_DIFFERENTIATION_VERSION = "6C.2"
ADAPTIVE_QUALITY_VERSION = "6D.1"
VISUAL_ACCEPTANCE_VERSION = "6E.2"


@dataclass(frozen=True, slots=True)
class StructuralCompilationReport:
    compiler_version: str
    template_version: str
    hierarchy_version: str
    source_program_id: str
    silhouette_features: int
    surface_features: int
    compound_children: int
    normalized_anchors: int
    mirror_groups: int
    volumetric_silhouette_features: int
    volumetric_compound_parents: int
    volumetric_compound_children: int
    body_profile: str
    style_profile: str
    grammar_signature: str
    advanced_fields: int
    adaptive_quality: bool
    morphology_profile: str
    morphology_fields: int

    def validate(self, expected_features: int) -> None:
        if self.compiler_version != STRUCTURAL_COMPILER_VERSION:
            raise RuntimeError("Unexpected structural compiler version.")
        if self.template_version != STRUCTURAL_TEMPLATE_VERSION:
            raise RuntimeError("Unexpected structural template version.")
        if self.hierarchy_version != STRUCTURAL_HIERARCHY_VERSION:
            raise RuntimeError("Unexpected structural hierarchy version.")
        represented = (
            self.silhouette_features
            + self.surface_features
            + self.compound_children
        )
        if represented != expected_features:
            raise RuntimeError("Structural compiler lost semantic features.")
        if not 0 <= self.volumetric_silhouette_features <= self.silhouette_features:
            raise RuntimeError("Invalid volumetric-silhouette count.")
        if not 0 <= self.volumetric_compound_parents <= self.surface_features:
            raise RuntimeError("Invalid volumetric-compound count.")
        if not 0 <= self.volumetric_compound_children <= self.compound_children:
            raise RuntimeError("Invalid volumetric-child count.")
        if not self.body_profile or not self.style_profile:
            raise RuntimeError("Structural compiler lost its grammar profile.")
        if not self.grammar_signature:
            raise RuntimeError("Structural compiler lost its grammar signature.")
        if self.advanced_fields < 0:
            raise RuntimeError("Structural compiler reported invalid advanced fields.")
        if not self.morphology_profile or self.morphology_fields < 3:
            raise RuntimeError("Structural compiler lost body morphogenesis.")


@dataclass(frozen=True, slots=True)
class StructuralCompilationResult:
    motor_program: dict[str, Any]
    structural_program: StructuralDesignProgram
    semantic_compilation: SemanticCompilationResult
    grammar: DesignGrammarPlan
    report: StructuralCompilationReport


class StructuralSemanticCompiler:
    """Apply structural roles and visual hierarchy to Motor DOBO JSON."""

    @classmethod
    def compile(
        cls,
        program: DesignSemanticProgram,
        structural: StructuralDesignProgram | None = None,
    ) -> StructuralCompilationResult:
        program.validate()
        structural = structural or StructuralVocabularyResolver.resolve(program)
        structural.validate(expected_features=len(program.features))
        grammar = DesignGrammarResolver.resolve(program, structural)
        semantic = SemanticToMotorCompiler.compile(program)
        motor = deepcopy(semantic.motor_program)
        morphology = StructuralMorphogenesisResolver.resolve(program, grammar)
        morphology_ids = StructuralBodySynthesizer.apply(
            motor,
            program,
            grammar,
            morphology,
        )
        hierarchy = motor["hierarchy_program"]
        templates = {item["id"]: item for item in hierarchy["templates"]}
        roots = {item["id"]: item for item in hierarchy["roots"]}
        semantic_features = {feature.id: feature for feature in program.features}
        structural_features = {
            feature.semantic_feature_id: feature for feature in structural.features
        }
        grammar_features = {
            feature.semantic_feature_id: feature for feature in grammar.features
        }
        volumetric_silhouette_ids: set[str] = set()
        volumetric_compound_ids: set[str] = set()
        volumetric_child_ids: set[str] = set()

        normalized = 0
        for feature_id, resolved in structural_features.items():
            if resolved.parent_feature_id is not None:
                continue
            node = roots[feature_id]
            semantic_feature = semantic_features[feature_id]
            grammar_feature = grammar_features[feature_id]
            cls._apply_body_anchor(node, resolved, semantic_feature, program)
            normalized += 1
            if grammar_feature.mass_strategy == "silhouette_mass":
                template = templates[f"{feature_id}_template"]
                cls._promote_silhouette_to_volumetric_mass(
                    motor,
                    node=node,
                    template=template,
                    resolved=resolved,
                    semantic_feature=semantic_feature,
                    grammar_feature=grammar_feature,
                    grammar=grammar,
                    program=program,
                )
                volumetric_silhouette_ids.add(feature_id)
            elif grammar_feature.mass_strategy == "compound_mass":
                template = templates[f"{feature_id}_template"]
                cls._promote_muzzle_to_volumetric_mass(
                    motor,
                    node=node,
                    template=template,
                    semantic_feature=semantic_feature,
                    grammar=grammar,
                    program=program,
                )
                volumetric_compound_ids.add(feature_id)
            elif resolved.structural_role == "silhouette":
                template = templates[f"{feature_id}_template"]
                cls._apply_silhouette_template(template, motor)

        for child_id, resolved in structural_features.items():
            if resolved.parent_feature_id is None:
                continue
            grammar_feature = grammar_features[child_id]
            if grammar_feature.mass_strategy == "compound_child_mass":
                parent_feature = semantic_features[resolved.parent_feature_id]
                child_feature = semantic_features[child_id]
                cls._promote_compound_child_to_volumetric_mass(
                    motor,
                    resolved=resolved,
                    parent_feature=parent_feature,
                    child_feature=child_feature,
                    grammar=grammar,
                    program=program,
                )
                volumetric_child_ids.add(child_id)
                normalized += 1
                continue
            child_node = roots.pop(child_id)
            parent_node = roots[resolved.parent_feature_id]
            parent_feature = semantic_features[resolved.parent_feature_id]
            child_feature = semantic_features[child_id]
            child_node.pop("surface_anchor", None)
            child_node["transform"] = cls._child_transform(
                resolved,
                parent_feature=parent_feature,
                child_feature=child_feature,
                body_width_mm=program.body.width_mm,
                body_height_mm=program.body.height_mm,
            )
            parent_node.setdefault("children", []).append(child_node)
            normalized += 1

        ordered_ids = [feature.id for feature in program.features]
        promoted_ids = (
            volumetric_silhouette_ids
            | volumetric_compound_ids
            | volumetric_child_ids
        )
        hierarchy["roots"] = [
            roots[item]
            for item in ordered_ids
            if item in roots and item not in promoted_ids
        ]
        hierarchy["templates"] = [
            template
            for template in hierarchy["templates"]
            if not any(
                template["id"] == f"{feature_id}_template"
                for feature_id in promoted_ids
            )
        ]
        cls._apply_mirror_consistency(hierarchy["roots"], structural)
        cls._apply_visual_adjacency(motor, structural)
        cls._reserve_promoted_mass_grid(motor, promoted_ids)
        advanced_fields = cls._apply_adaptive_quality(motor)
        output_id = f"structural_{semantic.report.output_program_id}"
        motor["id"] = output_id
        motor["output"]["basename"] = output_id
        motor["output"]["directory"] = (
            "outputs/product_generators/design_interpreter/" + output_id
        )
        report = StructuralCompilationReport(
            compiler_version=STRUCTURAL_COMPILER_VERSION,
            template_version=STRUCTURAL_TEMPLATE_VERSION,
            hierarchy_version=STRUCTURAL_HIERARCHY_VERSION,
            source_program_id=program.id,
            silhouette_features=sum(
                feature.structural_role == "silhouette"
                for feature in structural.features
            ),
            surface_features=sum(
                feature.structural_role in {"surface", "texture"}
                for feature in structural.features
            ),
            compound_children=sum(
                feature.structural_role == "compound_child"
                for feature in structural.features
            ),
            normalized_anchors=normalized,
            mirror_groups=sum(group.kind == "mirror_pair" for group in structural.groups),
            volumetric_silhouette_features=len(volumetric_silhouette_ids),
            volumetric_compound_parents=len(volumetric_compound_ids),
            volumetric_compound_children=len(volumetric_child_ids),
            body_profile=grammar.body_profile,
            style_profile=grammar.style.name,
            grammar_signature=grammar.signature,
            advanced_fields=advanced_fields,
            adaptive_quality=advanced_fields > 0,
            morphology_profile=morphology.profile,
            morphology_fields=len(morphology_ids),
        )
        report.validate(len(program.features))
        return StructuralCompilationResult(
            motor_program=motor,
            structural_program=structural,
            semantic_compilation=semantic,
            grammar=grammar,
            report=report,
        )

    @staticmethod
    def _apply_body_anchor(
        node: dict[str, Any],
        resolved: StructuralFeature,
        semantic_feature,
        program: DesignSemanticProgram,
    ) -> None:
        anchor = node["surface_anchor"]
        if resolved.attachment_mode == "body_silhouette":
            # Keep crown features readable from the front. Large azimuths made
            # planar templates appear edge-on as detached lateral plates.
            anchor["azimuth_degrees"] = 60.0 * resolved.anchor.horizontal
            height_extent = 0.5 * (
                semantic_feature.size.height_ratio * program.body.height_mm
            )
            usable_height = 0.85 * program.body.height_mm
            safe_top = max(0.65, 0.93 - height_extent / usable_height)
            anchor["height_ratio"] = min(resolved.anchor.vertical, safe_top)
            anchor["offset_mm"] = -max(
                0.45,
                0.35 * semantic_feature.size.depth_mm,
            )
        else:
            centers = {
                "front": 0.0,
                "upper": 0.0,
                "lower": 0.0,
                "left": -72.0,
                "right": 72.0,
                "back": 180.0,
                "all_around": 0.0,
            }
            spans = {
                "front": 55.0,
                "upper": 55.0,
                "lower": 55.0,
                "left": 35.0,
                "right": 35.0,
                "back": 45.0,
                "all_around": 180.0,
            }
            anchor["azimuth_degrees"] = (
                centers[resolved.anchor.region]
                + spans[resolved.anchor.region] * resolved.anchor.horizontal
            )
            anchor["height_ratio"] = resolved.anchor.vertical
        anchor["roll_degrees"] = resolved.anchor.roll_degrees

    @staticmethod
    def _apply_silhouette_template(
        template: dict[str, Any], motor_program: dict[str, Any]
    ) -> None:
        voxel = float(motor_program["grid"]["voxel_mm"])
        template["blend_mm"] = max(float(template["blend_mm"]), 1.4 * voxel)
        # Silhouette pieces remain within semantic manufacturability depth, but
        # receive enough implicit blending to become part of the body mass.

    @staticmethod
    def _promote_silhouette_to_volumetric_mass(
        motor_program: dict[str, Any],
        *,
        node: dict[str, Any],
        template: dict[str, Any],
        resolved: StructuralFeature,
        semantic_feature,
        grammar_feature: GrammarFeaturePlan,
        grammar: DesignGrammarPlan,
        program: DesignSemanticProgram,
    ) -> None:
        """Turn any grammar silhouette lobe into one or more fused body fields."""
        width = max(
            semantic_feature.size.width_ratio * program.body.width_mm,
            2.0 * program.manufacturing.minimum_feature_mm,
        ) * grammar.style.silhouette_scale
        height = max(
            semantic_feature.size.height_ratio * program.body.height_mm,
            2.0 * program.manufacturing.minimum_feature_mm,
        ) * grammar.style.silhouette_scale
        half_width = max(0.5 * width, 0.105 * program.body.width_mm)
        half_height = max(0.5 * height, 0.10 * program.body.height_mm)
        half_depth = max(
            0.32 * min(2.0 * half_width, 2.0 * half_height),
            2.5 * semantic_feature.size.depth_mm * grammar.style.depth_scale,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        semantic_region = semantic_feature.anchor.region
        if semantic_region in {"upper", "front"}:
            side = -1.0 if resolved.anchor.horizontal < 0.0 else 1.0
            shaped_lobe = grammar_feature.shape_profile in {
                "pointed",
                "elongated",
                "leaf",
                "tapered",
            }
            vertical_ratio = {
                "pointed": 0.30,
                "elongated": 0.36,
                "leaf": 0.36,
                "tapered": 0.30,
            }.get(grammar_feature.shape_profile, 0.25)
            horizontal_ratio = (
                0.25
                if grammar_feature.shape_profile in {"elongated", "leaf"}
                else 0.31
            )
            center = [
                side
                * (horizontal_ratio if shaped_lobe else 0.38)
                * program.body.width_mm,
                (
                    -0.06
                    if grammar_feature.shape_profile in {"elongated", "leaf"}
                    else (-0.12 if shaped_lobe else -0.16)
                )
                * program.body.depth_mm,
                vertical_ratio * program.body.height_mm,
            ]
        else:
            region_center = {
                "left": -90.0,
                "right": 90.0,
                "back": 180.0,
                "all_around": 0.0,
                "lower": 0.0,
            }.get(semantic_region, 0.0)
            span = 180.0 if semantic_region == "all_around" else 45.0
            angle = radians(region_center + span * semantic_feature.anchor.horizontal)
            radial_ratio = (
                0.36 if grammar_feature.shape_profile == "leaf" else 0.43
            )
            center = [
                radial_ratio * program.body.width_mm * sin(angle),
                -radial_ratio * program.body.depth_mm * cos(angle),
                (semantic_feature.anchor.vertical - 0.5)
                * 0.78
                * program.body.height_mm,
            ]
            if grammar_feature.shape_profile == "leaf":
                # A radial botanical leaf is a low, fused surface lobe.  Keeping
                # its crown below the opening prevents the arch-like handles
                # seen when a tall leaf merely touches the rim.
                center[2] = (
                    0.15
                    + 0.18 * (semantic_feature.anchor.vertical - 0.5)
                ) * program.body.height_mm
        if grammar_feature.shape_profile == "elongated":
            half_width = min(half_width, 0.10 * program.body.width_mm)
            half_height = max(half_height, 0.22 * program.body.height_mm)
        elif grammar_feature.shape_profile == "leaf":
            if semantic_region in {"upper", "front"}:
                # Long vertical leaf masses provide a rabbit silhouette that
                # cannot collapse back into short cat-like ears.
                half_width = min(half_width, 0.105 * program.body.width_mm)
                half_height = max(half_height, 0.22 * program.body.height_mm)
            else:
                half_width = min(half_width, 0.10 * program.body.width_mm)
                half_height = min(half_height, 0.12 * program.body.height_mm)
                half_depth = max(half_depth, 0.08 * program.body.depth_mm)
        elif grammar_feature.shape_profile == "tapered":
            half_width *= 0.82
        field_id = f"{semantic_feature.id}__silhouette_mass"
        field = {
            "id": field_id,
            "center": center,
            "radii": [half_width, half_depth, half_height],
        }
        if grammar_feature.shape_profile in {"elongated", "leaf"}:
            field.update(kind="leaf", round_mm=max(0.6, 0.18 * half_depth))
        elif grammar_feature.shape_profile in {"pointed", "tapered"}:
            field.update(kind="pointed", round_mm=max(0.6, 0.16 * half_width))
        motor_program["fields"].append(field)
        motor_program["composition"]["field_ids"].append(field_id)
        voxel = float(motor_program["grid"]["voxel_mm"])
        motor_program["composition"]["blend_mm"] = min(
            float(motor_program["composition"]["blend_mm"]),
            max(grammar.style.fusion_mm, 4.0 * voxel),
        )
        _ = node, template

    @staticmethod
    def _promote_muzzle_to_volumetric_mass(
        motor_program: dict[str, Any],
        *,
        node: dict[str, Any],
        template: dict[str, Any],
        semantic_feature,
        grammar: DesignGrammarPlan,
        program: DesignSemanticProgram,
    ) -> None:
        width = max(
            semantic_feature.size.width_ratio * program.body.width_mm,
            3.0 * program.manufacturing.minimum_feature_mm,
        )
        height = max(
            semantic_feature.size.height_ratio * program.body.height_mm,
            3.0 * program.manufacturing.minimum_feature_mm,
        )
        half_depth = max(
            0.18 * min(width, height),
            2.0 * semantic_feature.size.depth_mm * grammar.style.depth_scale,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        center_z = -0.075 * program.body.height_mm
        body_front_y = front_surface_y(
            motor_program,
            x=0.0,
            z=center_z,
        )
        penetration_mm = max(
            0.75 * float(motor_program["composition"]["blend_mm"]),
            0.75 * float(motor_program["vessel"]["wall_mm"]),
            2.5 * float(motor_program["grid"]["voxel_mm"]),
        )
        field_id = f"{semantic_feature.id}__compound_mass"
        field = {
            "id": field_id,
            "center": [
                0.0,
                body_front_y - half_depth + penetration_mm,
                center_z,
            ],
            "radii": [0.5 * width, half_depth, 0.5 * height],
        }
        motor_program["fields"].append(field)
        motor_program["composition"]["field_ids"].append(field_id)
        voxel = float(motor_program["grid"]["voxel_mm"])
        motor_program["composition"]["blend_mm"] = min(
            float(motor_program["composition"]["blend_mm"]),
            max(grammar.style.fusion_mm, 4.0 * voxel),
        )
        _ = node, template

    @staticmethod
    def _promote_compound_child_to_volumetric_mass(
        motor_program: dict[str, Any],
        *,
        resolved: StructuralFeature,
        parent_feature,
        child_feature,
        grammar: DesignGrammarPlan,
        program: DesignSemanticProgram,
    ) -> None:
        parent_width = max(
            parent_feature.size.width_ratio * program.body.width_mm,
            3.0 * program.manufacturing.minimum_feature_mm,
        )
        parent_height = max(
            parent_feature.size.height_ratio * program.body.height_mm,
            3.0 * program.manufacturing.minimum_feature_mm,
        )
        parent_half_depth = max(
            0.18 * min(parent_width, parent_height),
            2.0 * parent_feature.size.depth_mm * grammar.style.depth_scale,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        child_width = max(
            child_feature.size.width_ratio * program.body.width_mm,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        child_height = max(
            child_feature.size.height_ratio * program.body.height_mm,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        child_half_depth = max(
            0.22 * min(child_width, child_height),
            1.5 * child_feature.size.depth_mm * grammar.style.depth_scale,
            1.5 * program.manufacturing.minimum_feature_mm,
        )
        parent_field_id = f"{parent_feature.id}__compound_mass"
        parent_field = next(
            (
                field
                for field in motor_program["fields"]
                if field["id"] == parent_field_id
            ),
            None,
        )
        if parent_field is None:
            raise RuntimeError(
                "Compound child requires its promoted parent mass."
            )
        parent_center_y = float(parent_field["center"][1])
        parent_center_z = float(parent_field["center"][2])
        parent_half_depth = float(parent_field["radii"][1])
        if grammar.style.name == "organic":
            child_exposure_factor = 0.05
        elif grammar.style.name == "childlike":
            minimum_visible_mm = max(
                2.0,
                1.95 * program.manufacturing.minimum_feature_mm,
            )
            child_exposure_factor = min(
                0.45,
                max(
                    0.05,
                    1.0 - minimum_visible_mm / child_half_depth,
                ),
            )
        else:
            child_exposure_factor = -0.30
        field_id = f"{child_feature.id}__compound_child_mass"
        field = {
            "id": field_id,
            "center": [
                resolved.anchor.horizontal * parent_width,
                parent_center_y
                - parent_half_depth
                + child_exposure_factor * child_half_depth,
                parent_center_z
                + (resolved.anchor.vertical - 0.5) * parent_height,
            ],
            "radii": [
                0.5 * child_width,
                child_half_depth,
                0.5 * child_height,
            ],
        }
        if child_feature.form_hint == "point":
            if grammar.style.name == "childlike":
                # A pointed semantic nose remains compact and softly rounded;
                # the pointed primitive is reserved for silhouette masses such
                # as ears, where its apex is visually meaningful.
                field["radii"][0] *= 0.84
                field["radii"][2] *= 0.72
            else:
                field.update(
                    kind="pointed",
                    round_mm=max(0.5, 0.16 * min(field["radii"])),
                )
        motor_program["fields"].append(field)
        motor_program["composition"]["field_ids"].append(field_id)

    @staticmethod
    def _reserve_promoted_mass_grid(
        motor_program: dict[str, Any], promoted_ids: set[str]
    ) -> None:
        if not promoted_ids:
            return
        voxel = float(motor_program["grid"]["voxel_mm"])
        blend = float(motor_program["composition"]["blend_mm"])
        front_reserve = max(6.0, 2.0 * voxel, 1.5 * blend)
        motor_program["grid"]["minimum"][1] = (
            float(motor_program["grid"]["minimum"][1]) - front_reserve
        )

    @staticmethod
    def _apply_adaptive_quality(motor_program: dict[str, Any]) -> int:
        """Select a deterministic sub-30-second profile for advanced fields."""
        advanced = sum(
            str(field.get("kind", "ellipsoid")) != "ellipsoid"
            for field in motor_program["fields"]
            if field["id"] in set(motor_program["composition"]["field_ids"])
        )
        if advanced:
            motor_program["grid"]["voxel_mm"] = max(
                float(motor_program["grid"]["voxel_mm"]),
                0.72,
            )
            voxel = float(motor_program["grid"]["voxel_mm"])
            reserve = max(6.0, 8.0 * voxel)
            for axis in (0, 1):
                motor_program["grid"]["minimum"][axis] = (
                    float(motor_program["grid"]["minimum"][axis]) - reserve
                )
                motor_program["grid"]["maximum"][axis] = (
                    float(motor_program["grid"]["maximum"][axis]) + reserve
                )
            motor_program["grid"]["maximum"][2] = (
                float(motor_program["grid"]["maximum"][2]) + reserve
            )
            motor_program.pop("mesh_quality", None)
            motor_program["output"]["max_generation_seconds"] = 30.0
        return advanced

    @staticmethod
    def _child_transform(
        resolved: StructuralFeature,
        *,
        parent_feature,
        child_feature,
        body_width_mm: float,
        body_height_mm: float,
    ) -> dict[str, Any]:
        parent_height = parent_feature.size.height_ratio * body_height_mm
        parent_depth = parent_feature.size.depth_mm
        child_depth = child_feature.size.depth_mm
        return {
            "translate": [
                resolved.anchor.horizontal
                * parent_feature.size.width_ratio
                * body_width_mm,
                -max(0.2, parent_depth - 0.55 * child_depth),
                (resolved.anchor.vertical - 0.5) * parent_height,
            ],
            "rotate_degrees": [0.0, 0.0, resolved.anchor.roll_degrees],
        }

    @staticmethod
    def _apply_mirror_consistency(
        roots: list[dict[str, Any]], structural: StructuralDesignProgram
    ) -> None:
        by_id = {root["id"]: root for root in roots}
        for group in structural.groups:
            if group.kind != "mirror_pair" or len(group.member_ids) != 2:
                continue
            first = by_id.get(group.member_ids[0])
            second = by_id.get(group.member_ids[1])
            if first is None or second is None:
                continue
            first_anchor = first.get("surface_anchor")
            second_anchor = second.get("surface_anchor")
            if not isinstance(first_anchor, dict) or not isinstance(second_anchor, dict):
                continue
            magnitude = 0.5 * (
                abs(float(first_anchor["azimuth_degrees"]))
                + abs(float(second_anchor["azimuth_degrees"]))
            )
            height = 0.5 * (
                float(first_anchor["height_ratio"])
                + float(second_anchor["height_ratio"])
            )
            first_sign = (
                -1.0
                if float(first_anchor["azimuth_degrees"]) < 0.0
                else 1.0
            )
            second_sign = (
                -1.0
                if float(second_anchor["azimuth_degrees"]) < 0.0
                else 1.0
            )
            if first_sign == second_sign:
                first_sign, second_sign = -1.0, 1.0
            first_anchor["azimuth_degrees"] = first_sign * magnitude
            second_anchor["azimuth_degrees"] = second_sign * magnitude
            first_anchor["height_ratio"] = height
            second_anchor["height_ratio"] = height

    @staticmethod
    def _apply_visual_adjacency(
        motor_program: dict[str, Any], structural: StructuralDesignProgram
    ) -> None:
        constraints = motor_program["hierarchy_program"]["layout_constraints"]
        ignored = {
            tuple(sorted((str(pair[0]), str(pair[1]))))
            for pair in constraints.get("ignored_pairs", [])
        }
        features = tuple(structural.features)
        adjacent_zones = {
            ("upper_face", "mid_face"),
            ("mid_face", "lower_face"),
        }
        for index, first in enumerate(features):
            for second in features[index + 1 :]:
                zones = (first.visual_zone, second.visual_zone)
                if zones in adjacent_zones or zones[::-1] in adjacent_zones:
                    ignored.add(
                        tuple(
                            sorted(
                                (
                                    first.semantic_feature_id,
                                    second.semantic_feature_id,
                                )
                            )
                        )
                    )
        constraints["ignored_pairs"] = [list(pair) for pair in sorted(ignored)]
