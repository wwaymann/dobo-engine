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

_VOLUMETRIC_SILHOUETTE_CONCEPTS = {"ear", "oreja"}
_VOLUMETRIC_COMPOUND_CONCEPTS = {"muzzle", "hocico"}


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
        volumetric_silhouette_ids: set[str] = set()
        volumetric_compound_ids: set[str] = set()
        volumetric_child_ids: set[str] = set()

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
                if semantic_feature.concept.strip().lower() in (
                    _VOLUMETRIC_SILHOUETTE_CONCEPTS
                ):
                    cls._promote_ear_to_volumetric_mass(
                        motor,
                        node=node,
                        template=template,
                        resolved=resolved,
                        semantic_feature=semantic_feature,
                        program=program,
                    )
                    volumetric_silhouette_ids.add(feature_id)
                else:
                    cls._apply_silhouette_template(template, motor)
            elif (
                semantic_feature.concept.strip().lower()
                in _VOLUMETRIC_COMPOUND_CONCEPTS
                and resolved.geometric_operation == "add"
            ):
                template = templates[f"{feature_id}_template"]
                cls._promote_muzzle_to_volumetric_mass(
                    motor,
                    node=node,
                    template=template,
                    semantic_feature=semantic_feature,
                    program=program,
                )
                volumetric_compound_ids.add(feature_id)

        for child_id, resolved in structural_features.items():
            if resolved.parent_feature_id is None:
                continue
            if resolved.parent_feature_id in volumetric_compound_ids:
                parent_feature = semantic_features[resolved.parent_feature_id]
                child_feature = semantic_features[child_id]
                cls._promote_compound_child_to_volumetric_mass(
                    motor,
                    resolved=resolved,
                    parent_feature=parent_feature,
                    child_feature=child_feature,
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
    def _promote_ear_to_volumetric_mass(
        motor_program: dict[str, Any],
        *,
        node: dict[str, Any],
        template: dict[str, Any],
        resolved: StructuralFeature,
        semantic_feature,
        program: DesignSemanticProgram,
    ) -> None:
        """Turn an ear-like silhouette feature into a fused body field.

        Surface features inherit the tangent frame of the vessel. That is ideal
        for relief, but it made ears into thin side plates. A body field is a
        true three-dimensional mass, participates in the vessel smooth union,
        and is not incorrectly constrained as shallow surface relief.
        """
        width = max(
            semantic_feature.size.width_ratio * program.body.width_mm,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        height = max(
            semantic_feature.size.height_ratio * program.body.height_mm,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        half_width = max(0.5 * width, 0.105 * program.body.width_mm)
        half_height = max(0.5 * height, 0.10 * program.body.height_mm)
        half_depth = max(
            0.32 * min(2.0 * half_width, 2.0 * half_height),
            2.5 * semantic_feature.size.depth_mm,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        side = -1.0 if resolved.anchor.horizontal < 0.0 else 1.0
        field_id = f"{semantic_feature.id}__silhouette_mass"
        field = {
            "id": field_id,
            "center": [
                side * 0.38 * program.body.width_mm,
                -0.16 * program.body.depth_mm,
                0.25 * program.body.height_mm,
            ],
            "radii": [half_width, half_depth, half_height],
        }
        motor_program["fields"].append(field)
        motor_program["composition"]["field_ids"].append(field_id)
        voxel = float(motor_program["grid"]["voxel_mm"])
        motor_program["composition"]["blend_mm"] = min(
            float(motor_program["composition"]["blend_mm"]),
            max(3.6, 4.0 * voxel),
        )
        # Keep the node/template arguments explicit: their removal happens only
        # after every semantic feature has been processed, preserving stable
        # lookup and compilation traces during this pass.
        _ = node, template

    @staticmethod
    def _promote_muzzle_to_volumetric_mass(
        motor_program: dict[str, Any],
        *,
        node: dict[str, Any],
        template: dict[str, Any],
        semantic_feature,
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
            2.0 * semantic_feature.size.depth_mm,
            2.0 * program.manufacturing.minimum_feature_mm,
        )
        field_id = f"{semantic_feature.id}__compound_mass"
        field = {
            "id": field_id,
            "center": [
                0.0,
                -0.50 * program.body.depth_mm,
                -0.075 * program.body.height_mm,
            ],
            "radii": [0.5 * width, half_depth, 0.5 * height],
        }
        motor_program["fields"].append(field)
        motor_program["composition"]["field_ids"].append(field_id)
        voxel = float(motor_program["grid"]["voxel_mm"])
        motor_program["composition"]["blend_mm"] = min(
            float(motor_program["composition"]["blend_mm"]),
            max(3.6, 4.0 * voxel),
        )
        _ = node, template

    @staticmethod
    def _promote_compound_child_to_volumetric_mass(
        motor_program: dict[str, Any],
        *,
        resolved: StructuralFeature,
        parent_feature,
        child_feature,
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
            2.0 * parent_feature.size.depth_mm,
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
            1.5 * child_feature.size.depth_mm,
            1.5 * program.manufacturing.minimum_feature_mm,
        )
        parent_center_y = -0.50 * program.body.depth_mm
        parent_center_z = -0.075 * program.body.height_mm
        field_id = f"{child_feature.id}__compound_child_mass"
        motor_program["fields"].append(
            {
                "id": field_id,
                "center": [
                    resolved.anchor.horizontal * parent_width,
                    parent_center_y
                    - parent_half_depth
                    - 0.30 * child_half_depth,
                    parent_center_z
                    + (resolved.anchor.vertical - 0.5) * parent_height,
                ],
                "radii": [
                    0.5 * child_width,
                    child_half_depth,
                    0.5 * child_height,
                ],
            }
        )
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
