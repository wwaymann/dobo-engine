from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import cos, radians, sin
from typing import Any

from .complex_composition import (
    ComplexCompositionCompiler,
    ComplexCompositionResolver,
)
from .morphological_integration import AdvancedMorphologicalIntegration
from .continuous_morphological_fusion import ContinuousMorphologicalFusion
from .visible_morphological_continuity import VisibleMorphologicalContinuity
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
    complex_profile: str
    complex_nodes: int
    complex_edges: int
    hierarchy_depth: int
    structural_spans: int
    branch_nodes: int
    negative_volumes: int

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
        if not self.complex_profile or self.complex_nodes != expected_features:
            raise RuntimeError("Structural compiler lost complex topology.")
        if min(
            self.complex_edges,
            self.hierarchy_depth,
            self.structural_spans,
            self.branch_nodes,
            self.negative_volumes,
        ) < 0:
            raise RuntimeError("Structural compiler reported invalid topology counts.")


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
        complex_plan = ComplexCompositionResolver.resolve(program)
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
        complex_nodes = {node.id: node for node in complex_plan.nodes}
        for feature_id, topology_node in complex_nodes.items():
            cls._calibrate_complex_template(
                templates[f"{feature_id}_template"],
                topology_role=topology_node.role,
                semantic_feature=semantic_features[feature_id],
                program=program,
            )
            if topology_node.role == "span":
                cls._add_span_connector_templates(
                    hierarchy,
                    node=roots[feature_id],
                    template=templates[f"{feature_id}_template"],
                    minimum_feature_mm=program.manufacturing.minimum_feature_mm,
                    style_profile=grammar.style.name,
                )
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
            cls._integrate_complex_root_anchor(
                node,
                topology_role=complex_nodes[feature_id].role,
                semantic_feature=semantic_feature,
                program=program,
            )
            if (
                complex_nodes[feature_id].operation == "add"
                and complex_nodes[feature_id].role in {"branch", "terminal"}
                and grammar_feature.mass_strategy == "surface"
            ):
                cls._add_transition_mass_template(
                    hierarchy,
                    node=node,
                    template=templates[f"{feature_id}_template"],
                    topology_role=complex_nodes[feature_id].role,
                    style_profile=grammar.style.name,
                    minimum_feature_mm=program.manufacturing.minimum_feature_mm,
                    is_child=False,
                )
                cls._add_visible_root_flare_template(
                    hierarchy,
                    node=node,
                    template=templates[f"{feature_id}_template"],
                    topology_role=complex_nodes[feature_id].role,
                    style_profile=grammar.style.name,
                    minimum_feature_mm=program.manufacturing.minimum_feature_mm,
                )
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

        all_nodes = dict(roots)
        hierarchy_parents: dict[str, str] = {}
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
            child_node = all_nodes[child_id]
            parent_feature = semantic_features[resolved.parent_feature_id]
            child_feature = semantic_features[child_id]
            child_node.pop("surface_anchor", None)
            child_node["transform"] = cls._child_transform(
                resolved,
                parent_feature=parent_feature,
                child_feature=child_feature,
                body_width_mm=program.body.width_mm,
                body_height_mm=program.body.height_mm,
                minimum_feature_mm=program.manufacturing.minimum_feature_mm,
                topology_role=complex_nodes[child_id].role,
                parent_topology_role=complex_nodes[
                    resolved.parent_feature_id
                ].role,
            )
            if (
                complex_nodes[child_id].operation == "add"
                and complex_nodes[child_id].role in {"branch", "terminal"}
                and grammar_feature.mass_strategy == "surface"
            ):
                cls._add_transition_mass_template(
                    hierarchy,
                    node=child_node,
                    template=templates[f"{child_id}_template"],
                    topology_role=complex_nodes[child_id].role,
                    style_profile=grammar.style.name,
                    minimum_feature_mm=program.manufacturing.minimum_feature_mm,
                    is_child=True,
                )
                cls._add_visible_root_flare_template(
                    hierarchy,
                    node=child_node,
                    template=templates[f"{child_id}_template"],
                    topology_role=complex_nodes[child_id].role,
                    style_profile=grammar.style.name,
                    minimum_feature_mm=program.manufacturing.minimum_feature_mm,
                )
                parent_id = resolved.parent_feature_id
                parent_topology = complex_nodes[parent_id]
                if (
                    parent_topology.operation == "add"
                    and parent_topology.role in {"branch", "terminal"}
                ):
                    cls._add_hierarchy_bridge_template(
                        hierarchy,
                        parent_node=all_nodes[parent_id],
                        child_node=child_node,
                        child_template=templates[f"{child_id}_template"],
                        topology_role=complex_nodes[child_id].role,
                        style_profile=grammar.style.name,
                        minimum_feature_mm=program.manufacturing.minimum_feature_mm,
                    )
            hierarchy_parents[child_id] = resolved.parent_feature_id
            normalized += 1

        def hierarchy_level(feature_id: str) -> int:
            level = 0
            visited = {feature_id}
            current = feature_id
            while current in hierarchy_parents:
                current = hierarchy_parents[current]
                if current in visited:
                    raise RuntimeError("Structural hierarchy contains a cycle.")
                visited.add(current)
                level += 1
            return level

        for child_id in sorted(hierarchy_parents, key=hierarchy_level):
            parent_id = hierarchy_parents[child_id]
            all_nodes[parent_id].setdefault("children", []).append(
                all_nodes[child_id]
            )
            roots.pop(child_id, None)

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
        cls._ignore_hierarchy_contact(motor, hierarchy_parents)
        cls._classify_structural_depth_features(
            motor,
            complex_nodes=complex_nodes,
        )
        cls._reserve_promoted_mass_grid(motor, promoted_ids)
        advanced_fields = cls._apply_adaptive_quality(motor)
        ComplexCompositionCompiler.apply(motor, complex_plan)
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
            complex_profile=complex_plan.profile,
            complex_nodes=len(complex_plan.nodes),
            complex_edges=len(complex_plan.edges),
            hierarchy_depth=complex_plan.maximum_depth,
            structural_spans=complex_plan.span_count,
            branch_nodes=complex_plan.branch_count,
            negative_volumes=complex_plan.negative_volume_count,
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
    def _calibrate_complex_template(
        template: dict[str, Any],
        *,
        topology_role: str,
        semantic_feature,
        program: DesignSemanticProgram,
    ) -> None:
        """Give complex components real volume before hierarchical placement."""
        operation = str(template["operation"])
        minimum = float(program.manufacturing.minimum_feature_mm)
        body_depth = float(program.body.depth_mm)
        if operation == "add" and topology_role == "span":
            half_depth = max(
                float(template.get("half_depth_mm", semantic_feature.size.depth_mm)),
                0.052 * body_depth,
                2.2 * minimum,
            )
            template["half_depth_mm"] = half_depth
            template["round_mm"] = max(float(template.get("round_mm", 0.0)), 1.2)
            template["blend_mm"] = max(
                float(template["blend_mm"]),
                min(4.8, 0.72 * half_depth),
            )
        elif operation == "add" and topology_role in {"branch", "terminal"}:
            half_depth = max(
                0.048 * body_depth,
                (2.0 if topology_role == "branch" else 1.7) * minimum,
            )
            if template["kind"] == "ellipsoid":
                template["radii"][1] = max(
                    float(template["radii"][1]), half_depth
                )
            elif template["kind"] == "rounded_triangle_prism":
                template["half_depth_mm"] = max(
                    float(template["half_depth_mm"]), half_depth
                )
                template["round_mm"] = max(
                    float(template.get("round_mm", 0.0)), 1.0
                )
            template["blend_mm"] = max(
                float(template["blend_mm"]),
                min(4.2, 0.62 * half_depth),
            )

    @staticmethod
    def _integrate_complex_root_anchor(
        node: dict[str, Any],
        *,
        topology_role: str,
        semantic_feature,
        program: DesignSemanticProgram,
    ) -> None:
        if topology_role not in {"span", "branch", "terminal"}:
            return
        if semantic_feature.surface_effect not in {"raised", "marking"}:
            return
        anchor = node.get("surface_anchor")
        if not isinstance(anchor, dict):
            return
        if topology_role == "span":
            anchor["offset_mm"] = -max(
                1.2,
                0.28 * semantic_feature.size.depth_mm,
            )
            if semantic_feature.anchor.region == "upper":
                anchor["azimuth_degrees"] = (
                    72.0 * semantic_feature.anchor.horizontal
                )
                anchor["height_ratio"] = min(float(anchor["height_ratio"]), 0.79)
        else:
            anchor["offset_mm"] = -max(
                1.8,
                0.65 * semantic_feature.size.depth_mm,
                0.45 * program.manufacturing.minimum_wall_mm,
            )

    @staticmethod
    def _add_span_connector_templates(
        hierarchy: dict[str, Any],
        *,
        node: dict[str, Any],
        template: dict[str, Any],
        minimum_feature_mm: float,
        style_profile: str,
    ) -> None:
        """Add lateral fusion feet that a central span cutout cannot sever.

        A hollow arch must connect through material outside its opening.  The
        original single arched field could be detached when its subtractive
        child removed the narrow contact band against the vessel.  Two small
        rounded boxes now carry that load on either side of the opening and
        extend inward into the body field.
        """
        if (
            template.get("kind") != "arched_prism"
            or template.get("operation") != "add"
        ):
            return
        interface = AdvancedMorphologicalIntegration.span_interface(style_profile)
        continuity = ContinuousMorphologicalFusion.span_continuity(style_profile)
        visibility = VisibleMorphologicalContinuity.span_visible_root(style_profile)
        half_width = float(template["half_width_mm"])
        half_depth = float(template["half_depth_mm"])
        bottom = float(template["bottom_z_mm"])
        spring = float(template["spring_z_mm"])
        leg_height = max(spring - bottom, 2.8 * minimum_feature_mm)
        foot_half_width = max(
            0.16 * half_width,
            1.15 * minimum_feature_mm,
        )
        foot_half_height = max(
            0.34 * leg_height,
            1.4 * minimum_feature_mm,
        )
        foot_half_depth = max(
            0.82 * half_depth,
            2.0 * minimum_feature_mm,
        )
        foot_x = max(
            0.58 * half_width,
            half_width - 1.15 * foot_half_width,
        )
        foot_z = bottom + foot_half_height
        foot_y = max(0.9, continuity.inward_shift_scale * half_depth)
        connector_ids: list[str] = []
        for side, x in (("left", -foot_x), ("right", foot_x)):
            connector_id = f"{node['id']}_{side}_fusion_foot_template"
            flare_id = f"{node['id']}_{side}_visible_span_root_template"
            connector_ids.append(connector_id)
            base_blend = max(
                2.2,
                min(4.2, 0.68 * foot_half_depth),
            ) * interface.blend_scale * continuity.blend_scale
            if interface.kind == "ellipsoid":
                connector = {
                    "id": connector_id,
                    "operation": "add",
                    "blend_mm": min(4.4, base_blend),
                    "probe": [0.0, 0.0, 0.0],
                    "kind": "ellipsoid",
                    "center": [x, foot_y, foot_z],
                    "radii": [
                        interface.width_scale * continuity.width_scale * foot_half_width,
                        interface.depth_scale * continuity.depth_scale * foot_half_depth,
                        interface.height_scale * continuity.height_scale * foot_half_height,
                    ],
                }
            else:
                half_sizes = [
                    interface.width_scale * continuity.width_scale * foot_half_width,
                    interface.depth_scale * continuity.depth_scale * foot_half_depth,
                    interface.height_scale * continuity.height_scale * foot_half_height,
                ]
                connector = {
                    "id": connector_id,
                    "operation": "add",
                    "blend_mm": max(2.0, min(4.0, base_blend)),
                    "probe": [0.0, 0.0, 0.0],
                    "kind": "rounded_box",
                    "center": [x, foot_y, foot_z],
                    "half_sizes": half_sizes,
                    "round_mm": max(
                        0.65,
                        min(1.5, 0.32 * min(half_sizes)),
                    ),
                }
            flare_y = -max(
                0.25 * minimum_feature_mm,
                visibility.outward_shift_scale * half_depth,
            )
            flare_half = [
                max(
                    1.05 * minimum_feature_mm,
                    visibility.width_scale * foot_half_width,
                ),
                max(
                    1.55 * minimum_feature_mm,
                    visibility.depth_scale * foot_half_depth,
                ),
                max(
                    1.15 * minimum_feature_mm,
                    visibility.height_scale * foot_half_height,
                ),
            ]
            flare_blend = min(
                5.0,
                max(
                    1.6 * minimum_feature_mm,
                    base_blend * visibility.blend_scale,
                    0.50 * flare_half[1],
                ),
            )
            if visibility.kind == "ellipsoid":
                flare = {
                    "id": flare_id,
                    "operation": "add",
                    "blend_mm": flare_blend,
                    "probe": [0.0, 0.0, 0.0],
                    "kind": "ellipsoid",
                    "center": [x, flare_y, foot_z],
                    "radii": flare_half,
                }
            else:
                flare = {
                    "id": flare_id,
                    "operation": "add",
                    "blend_mm": flare_blend,
                    "probe": [0.0, 0.0, 0.0],
                    "kind": "rounded_box",
                    "center": [x, flare_y, foot_z],
                    "half_sizes": flare_half,
                    "round_mm": max(0.55, min(1.35, 0.28 * min(flare_half))),
                }
            hierarchy["templates"].append(connector)
            hierarchy["templates"].append(flare)
            connector_ids.append(flare_id)
        node["template_ids"].extend(connector_ids)

    @staticmethod
    def _add_transition_mass_template(
        hierarchy: dict[str, Any],
        *,
        node: dict[str, Any],
        template: dict[str, Any],
        topology_role: str,
        style_profile: str,
        minimum_feature_mm: float,
        is_child: bool,
    ) -> None:
        """Add a narrower/deeper SDF collar at an additive interface.

        The collar is owned by the same hierarchy node as the visible feature,
        so layout intentionally treats both templates as one compound component.
        Local +Y points into the body/parent surface. Keeping X/Z smaller than
        the visible component preserves silhouette while the deeper Y extent and
        stronger smooth-union radius create a continuous transition.
        """
        if template.get("operation") != "add":
            return
        if topology_role not in {"branch", "terminal"}:
            return

        def half_extents(source: dict[str, Any]) -> tuple[float, float, float]:
            kind = str(source.get("kind"))
            if kind in {"ellipsoid", "superellipsoid", "faceted_ellipsoid", "leaf", "pointed"}:
                radii = source["radii"]
                return float(radii[0]), float(radii[1]), float(radii[2])
            if kind == "rounded_box":
                half_sizes = source["half_sizes"]
                return float(half_sizes[0]), float(half_sizes[1]), float(half_sizes[2])
            if kind == "rounded_triangle_prism":
                vertices = source["vertices_xz"]
                return (
                    max(abs(float(point[0])) for point in vertices),
                    float(source["half_depth_mm"]),
                    max(abs(float(point[1])) for point in vertices),
                )
            if kind == "capsule":
                start = source["start"]
                end = source["end"]
                radius = float(source["radius_mm"])
                return (
                    0.5 * abs(float(end[0]) - float(start[0])) + radius,
                    0.5 * abs(float(end[1]) - float(start[1])) + radius,
                    0.5 * abs(float(end[2]) - float(start[2])) + radius,
                )
            raise ValueError(f"A.3 cannot derive transition extents for {kind!r}.")

        half_x, half_y, half_z = half_extents(template)
        policy = ContinuousMorphologicalFusion.transition_mass(
            style_name=style_profile,
            topology_role=topology_role,
            is_child=is_child,
        )
        transition_id = f"{node['id']}_continuous_transition_template"
        center_y = max(
            0.45 * minimum_feature_mm,
            policy.inward_shift_scale * half_y,
        )
        transition_half = [
            max(0.75 * minimum_feature_mm, policy.lateral_scale * half_x),
            max(1.35 * minimum_feature_mm, policy.depth_scale * half_y),
            max(0.75 * minimum_feature_mm, policy.vertical_scale * half_z),
        ]
        blend = min(
            5.2,
            max(
                1.5 * minimum_feature_mm,
                float(template.get("blend_mm", 1.0)) * policy.blend_scale,
                0.56 * transition_half[1],
            ),
        )
        if policy.kind == "ellipsoid":
            transition = {
                "id": transition_id,
                "operation": "add",
                "blend_mm": blend,
                "probe": [0.0, 0.0, 0.0],
                "kind": "ellipsoid",
                "center": [0.0, center_y, 0.0],
                "radii": transition_half,
            }
        else:
            round_mm = max(
                0.55,
                min(1.6, 0.30 * min(transition_half)),
            )
            transition = {
                "id": transition_id,
                "operation": "add",
                "blend_mm": blend,
                "probe": [0.0, 0.0, 0.0],
                "kind": "rounded_box",
                "center": [0.0, center_y, 0.0],
                "half_sizes": transition_half,
                "round_mm": round_mm,
            }
        hierarchy["templates"].append(transition)
        node.setdefault("template_ids", []).append(transition_id)

    @staticmethod
    def _add_visible_root_flare_template(
        hierarchy: dict[str, Any],
        *,
        node: dict[str, Any],
        template: dict[str, Any],
        topology_role: str,
        style_profile: str,
        minimum_feature_mm: float,
    ) -> None:
        """Add a controlled outward flare around an additive branch root."""
        if template.get("operation") != "add":
            return
        if topology_role not in {"branch", "terminal"}:
            return

        def half_extents(source: dict[str, Any]) -> tuple[float, float, float]:
            kind = str(source.get("kind"))
            if kind in {
                "ellipsoid",
                "superellipsoid",
                "faceted_ellipsoid",
                "leaf",
                "pointed",
            }:
                radii = source["radii"]
                return float(radii[0]), float(radii[1]), float(radii[2])
            if kind == "rounded_triangle_prism":
                vertices = source["vertices_xz"]
                return (
                    max(abs(float(point[0])) for point in vertices),
                    float(source["half_depth_mm"]),
                    max(abs(float(point[1])) for point in vertices),
                )
            if kind == "rounded_box":
                half_sizes = source["half_sizes"]
                return (
                    float(half_sizes[0]),
                    float(half_sizes[1]),
                    float(half_sizes[2]),
                )
            raise ValueError(f"A.4 cannot derive visible root extents for {kind!r}.")

        half_x, half_y, half_z = half_extents(template)
        policy = VisibleMorphologicalContinuity.root_flare(
            style_name=style_profile,
            topology_role=topology_role,
        )
        flare_id = f"{node['id']}_visible_root_flare_template"
        center_y = -max(
            0.25 * minimum_feature_mm,
            policy.outward_shift_scale * half_y,
        )
        flare_half = [
            max(0.95 * minimum_feature_mm, policy.lateral_scale * half_x),
            max(1.35 * minimum_feature_mm, policy.depth_scale * half_y),
            max(0.95 * minimum_feature_mm, policy.vertical_scale * half_z),
        ]
        blend = min(
            5.2,
            max(
                1.6 * minimum_feature_mm,
                float(template.get("blend_mm", 1.0)) * policy.blend_scale,
                0.48 * flare_half[1],
            ),
        )
        if policy.kind == "ellipsoid":
            flare = {
                "id": flare_id,
                "operation": "add",
                "blend_mm": blend,
                "probe": [0.0, 0.0, 0.0],
                "kind": "ellipsoid",
                "center": [0.0, center_y, 0.0],
                "radii": flare_half,
            }
        else:
            flare = {
                "id": flare_id,
                "operation": "add",
                "blend_mm": blend,
                "probe": [0.0, 0.0, 0.0],
                "kind": "rounded_box",
                "center": [0.0, center_y, 0.0],
                "half_sizes": flare_half,
                "round_mm": max(0.55, min(1.35, 0.28 * min(flare_half))),
            }
        hierarchy["templates"].append(flare)
        node.setdefault("template_ids", []).append(flare_id)

    @staticmethod
    def _add_hierarchy_bridge_template(
        hierarchy: dict[str, Any],
        *,
        parent_node: dict[str, Any],
        child_node: dict[str, Any],
        child_template: dict[str, Any],
        topology_role: str,
        style_profile: str,
        minimum_feature_mm: float,
    ) -> None:
        """Bridge additive parent/child branch hierarchy with a visible capsule."""
        translate = child_node.get("transform", {}).get("translate")
        if not isinstance(translate, list) or len(translate) != 3:
            return
        vector = [float(value) for value in translate]
        length = sum(value * value for value in vector) ** 0.5
        if length <= 2.2 * minimum_feature_mm:
            return

        kind = str(child_template.get("kind"))
        if kind in {
            "ellipsoid",
            "superellipsoid",
            "faceted_ellipsoid",
            "leaf",
            "pointed",
        }:
            radii = child_template["radii"]
            child_cross = min(float(radii[0]), float(radii[2]))
        elif kind == "rounded_triangle_prism":
            vertices = child_template["vertices_xz"]
            child_cross = min(
                max(abs(float(point[0])) for point in vertices),
                max(abs(float(point[1])) for point in vertices),
            )
        else:
            return

        policy = VisibleMorphologicalContinuity.hierarchy_bridge(
            style_name=style_profile,
            topology_role=topology_role,
        )
        start = [policy.start_fraction * value for value in vector]
        end = [policy.end_fraction * value for value in vector]
        radius = max(
            0.95 * minimum_feature_mm,
            min(0.22 * length, policy.radius_scale * child_cross),
        )
        bridge_id = f"{parent_node['id']}_{child_node['id']}_visible_bridge_template"
        bridge = {
            "id": bridge_id,
            "operation": "add",
            "blend_mm": min(
                4.8,
                max(
                    1.5 * minimum_feature_mm,
                    float(child_template.get("blend_mm", 1.0)) * policy.blend_scale,
                    0.75 * radius,
                ),
            ),
            "probe": [0.0, 0.0, 0.0],
            "kind": "capsule",
            "start": start,
            "end": end,
            "radius_mm": radius,
        }
        hierarchy["templates"].append(bridge)
        parent_node.setdefault("template_ids", []).append(bridge_id)

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
    def _classify_structural_depth_features(
        motor_program: dict[str, Any],
        *,
        complex_nodes: dict[str, Any],
    ) -> None:
        structural_roles = {"span", "branch", "terminal"}

        def belongs_to_structure(feature_id: str) -> bool:
            current = complex_nodes[feature_id]
            visited = {feature_id}
            while True:
                if current.role in structural_roles:
                    return True
                if current.parent_id is None:
                    return False
                if current.parent_id in visited:
                    raise RuntimeError("Complex structural depth graph contains a cycle.")
                visited.add(current.parent_id)
                current = complex_nodes[current.parent_id]

        identifiers = sorted(
            feature_id
            for feature_id in complex_nodes
            if belongs_to_structure(feature_id)
        )
        motor_program["hierarchy_program"]["feature_manufacturability"][
            "structural_depth_feature_ids"
        ] = identifiers

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
        minimum_feature_mm: float,
        topology_role: str,
        parent_topology_role: str,
    ) -> dict[str, Any]:
        parent_height = parent_feature.size.height_ratio * body_height_mm
        parent_depth = parent_feature.size.depth_mm
        child_depth = child_feature.size.depth_mm
        translate_y = -max(0.2, parent_depth - 0.55 * child_depth)
        depth_scale = 1.0
        if (
            resolved.geometric_operation == "subtract"
            or child_feature.surface_effect in {"cutout", "recessed"}
        ):
            translate_y = -max(1.2, parent_depth)
            if parent_topology_role == "terminal":
                translate_y = -max(
                    1.2,
                    2.0 * parent_depth + 0.55 * child_depth,
                )
            depth_scale = 1.0
        elif child_feature.surface_effect in {"raised", "marking"} and topology_role in {
            "branch",
            "terminal",
            "span",
        }:
            exposure = AdvancedMorphologicalIntegration.raised_child_exposure(
                parent_depth_mm=parent_depth,
                child_depth_mm=child_depth,
                minimum_feature_mm=minimum_feature_mm,
            )
            translate_y = exposure.translate_y_mm
            depth_scale = exposure.depth_scale
        parent_width = parent_feature.size.width_ratio * body_width_mm
        child_width = child_feature.size.width_ratio * body_width_mm
        spread = ContinuousMorphologicalFusion.attachment_spread(
            topology_role=topology_role,
            parent_width_mm=parent_width,
            child_width_mm=child_width,
        )
        return {
            "translate": [
                resolved.anchor.horizontal * parent_width * spread.lateral_scale,
                translate_y,
                (resolved.anchor.vertical - 0.5) * parent_height,
            ],
            "rotate_degrees": [0.0, 0.0, resolved.anchor.roll_degrees],
            "scale": [1.0, depth_scale, 1.0],
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

    @staticmethod
    def _ignore_hierarchy_contact(
        motor_program: dict[str, Any], parents: dict[str, str]
    ) -> None:
        """Allow the deliberate overlap that joins or carves parent features."""
        constraints = motor_program["hierarchy_program"]["layout_constraints"]
        ignored = {
            tuple(sorted((str(pair[0]), str(pair[1]))))
            for pair in constraints.get("ignored_pairs", [])
        }
        for child_id, parent_id in parents.items():
            ignored.add(tuple(sorted((child_id, parent_id))))
        def root_of(feature_id: str) -> str:
            visited = {feature_id}
            current = feature_id
            while current in parents:
                current = parents[current]
                if current in visited:
                    raise RuntimeError("Structural hierarchy contains a cycle.")
                visited.add(current)
            return current

        members_by_root: dict[str, list[str]] = {}
        for feature_id in set(parents) | set(parents.values()):
            members_by_root.setdefault(root_of(feature_id), []).append(feature_id)
        for members in members_by_root.values():
            for index, first in enumerate(sorted(set(members))):
                for second in sorted(set(members))[index + 1 :]:
                    ignored.add(tuple(sorted((first, second))))
        constraints["ignored_pairs"] = [list(pair) for pair in sorted(ignored)]
