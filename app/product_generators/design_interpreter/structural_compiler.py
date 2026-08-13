from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .semantic_compiler import SemanticCompilationResult, SemanticToMotorCompiler
from .semantic_contract import DesignSemanticProgram
from .structural_vocabulary import (
    StructuralDesignProgram,
    StructuralFeature,
    StructuralVocabularyResolver,
)


STRUCTURAL_COMPILER_VERSION = "4B.1"
STRUCTURAL_TEMPLATE_VERSION = "4C.1"
STRUCTURAL_HIERARCHY_VERSION = "4D.1"


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


@dataclass(frozen=True, slots=True)
class StructuralCompilationResult:
    motor_program: dict[str, Any]
    structural_program: StructuralDesignProgram
    semantic_compilation: SemanticCompilationResult
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
        semantic = SemanticToMotorCompiler.compile(program)
        motor = deepcopy(semantic.motor_program)
        hierarchy = motor["hierarchy_program"]
        templates = {item["id"]: item for item in hierarchy["templates"]}
        roots = {item["id"]: item for item in hierarchy["roots"]}
        semantic_features = {feature.id: feature for feature in program.features}
        structural_features = {
            feature.semantic_feature_id: feature for feature in structural.features
        }

        normalized = 0
        for feature_id, resolved in structural_features.items():
            if resolved.parent_feature_id is not None:
                continue
            node = roots[feature_id]
            semantic_feature = semantic_features[feature_id]
            cls._apply_body_anchor(node, resolved, semantic_feature, program)
            normalized += 1
            if resolved.structural_role == "silhouette":
                template = templates[f"{feature_id}_template"]
                cls._apply_silhouette_template(template, motor)

        for child_id, resolved in structural_features.items():
            if resolved.parent_feature_id is None:
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
        hierarchy["roots"] = [roots[item] for item in ordered_ids if item in roots]
        cls._apply_mirror_consistency(hierarchy["roots"], structural)
        cls._apply_visual_adjacency(motor, structural)
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
        )
        report.validate(len(program.features))
        return StructuralCompilationResult(
            motor_program=motor,
            structural_program=structural,
            semantic_compilation=semantic,
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
            anchor["azimuth_degrees"] = 105.0 * resolved.anchor.horizontal
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
