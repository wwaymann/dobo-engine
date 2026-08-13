from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .semantic_contract import DesignSemanticProgram, FeatureIntent, SemanticAnchor


COMPILER_VERSION = "3B.1"


@dataclass(frozen=True, slots=True)
class CompilationTrace:
    semantic_feature_id: str
    template_id: str
    node_id: str
    primitive_kind: str
    operation: str


@dataclass(frozen=True, slots=True)
class SemanticCompilationReport:
    compiler_version: str
    source_program_id: str
    output_program_id: str
    feature_traces: tuple[CompilationTrace, ...]
    compiled_relations: int
    ignored_overlap_pairs: tuple[tuple[str, str], ...]

    def validate(self, expected_features: int) -> None:
        if self.compiler_version != COMPILER_VERSION:
            raise RuntimeError("Unexpected semantic compiler version.")
        if len(self.feature_traces) != expected_features:
            raise RuntimeError("Not every semantic feature was compiled.")
        semantic_ids = [trace.semantic_feature_id for trace in self.feature_traces]
        if len(set(semantic_ids)) != len(semantic_ids):
            raise RuntimeError("Semantic compilation trace contains duplicates.")


@dataclass(frozen=True, slots=True)
class SemanticCompilationResult:
    motor_program: dict[str, Any]
    report: SemanticCompilationReport

    def write_json(self, path: str | Path) -> Path:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.motor_program, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target


class SemanticToMotorCompiler:
    """Compile semantic intent into the existing hierarchical motor vocabulary."""

    @classmethod
    def compile(cls, program: DesignSemanticProgram) -> SemanticCompilationResult:
        program.validate()
        body = program.body
        manufacturing = program.manufacturing
        width = body.width_mm
        depth = body.depth_mm
        height = body.height_mm
        wall = manufacturing.minimum_wall_mm
        base_z = -0.45 * height
        opening_z = 0.40 * height
        cavity_floor = base_z + max(1.6 * wall, 6.0)
        opening_radii = (
            0.5 * width * body.opening_width_ratio,
            0.5 * depth * body.opening_depth_ratio,
        )
        margin = max(8.0, 0.08 * max(width, depth, height))
        minimum_blend_mm = max(
            0.4,
            0.4 * manufacturing.minimum_feature_mm,
        )
        minimum_relief_depth_mm = min(
            0.8,
            min(feature.size.depth_mm for feature in program.features),
        )

        templates: list[dict[str, Any]] = []
        roots: list[dict[str, Any]] = []
        traces: list[CompilationTrace] = []
        for feature in program.features:
            template_id = f"{feature.id}_template"
            template, transform = cls._compile_feature(
                feature,
                template_id=template_id,
                body_width_mm=width,
                body_height_mm=height,
                minimum_feature_mm=manufacturing.minimum_feature_mm,
                minimum_blend_mm=minimum_blend_mm,
                minimum_relief_depth_mm=minimum_relief_depth_mm,
                maximum_relief_depth_mm=manufacturing.maximum_relief_depth_mm,
            )
            templates.append(template)
            node: dict[str, Any] = {
                "id": feature.id,
                "template_ids": [template_id],
                "surface_anchor": cls._compile_anchor(feature.anchor, feature),
            }
            if transform is not None:
                node["transform"] = transform
            roots.append(node)
            traces.append(
                CompilationTrace(
                    semantic_feature_id=feature.id,
                    template_id=template_id,
                    node_id=feature.id,
                    primitive_kind=str(template["kind"]),
                    operation=str(template["operation"]),
                )
            )

        ignored_pairs = tuple(
            sorted(
                {
                    tuple(sorted((relation.subject_id, relation.object_id)))
                    for relation in program.relations
                    if relation.kind
                    in {
                        "above",
                        "aligned_with",
                        "below",
                        "centered_on",
                        "grouped_with",
                    }
                }
            )
        )
        maximum_depth = manufacturing.maximum_relief_depth_mm
        motor_id = f"compiled_{program.id}"
        motor_program: dict[str, Any] = {
            "id": motor_id,
            "grid": {
                "minimum": [
                    -0.5 * width - margin,
                    -0.5 * depth - margin,
                    base_z - margin,
                ],
                "maximum": [
                    0.5 * width + margin,
                    0.5 * depth + margin,
                    0.5 * height + margin,
                ],
                "voxel_mm": cls._voxel_size(width, depth, height),
            },
            "fields": cls._body_fields(program),
            "composition": {
                "field_ids": ["body", "front_mass"],
                "blend_mm": max(4.0, 0.075 * min(width, depth)),
            },
            "vessel": {
                "wall_mm": wall,
                "base_z_mm": base_z,
                "cavity_floor_z_mm": cavity_floor,
                "opening_center": [0.0, 0.0],
                "opening_radii": list(opening_radii),
                "opening_start_z_mm": opening_z,
                "opening_blend_mm": max(2.0, 0.04 * min(width, depth)),
                "rim_round_mm": max(1.2, 0.35 * wall),
                "drain_center": [0.0, 0.0],
                "drain_radius_mm": max(2.5, 0.7 * wall),
                "drain_start_z_mm": base_z - 3.0,
                "drain_end_z_mm": cavity_floor + 3.0,
            },
            "mesh_quality": cls._mesh_quality(),
            "hierarchy_program": {
                "adaptive_refinement": {
                    "surface_band_mm": 1.2,
                    "size_band_ratio": 0.45,
                    "maximum_band_mm": 2.4,
                    "small_feature_threshold_mm": max(
                        3.0, 2.5 * manufacturing.minimum_feature_mm
                    ),
                    "detail_subdivision_passes": 1,
                },
                "proportional_scaling": {
                    "reference_radius_mm": 0.35 * width,
                    "reference_height_mm": opening_z - base_z,
                    "minimum_scale": 0.8,
                    "maximum_scale": 1.3,
                    "scale_depth": False,
                },
                "layout_constraints": {
                    "minimum_clearance_mm": manufacturing.minimum_feature_mm / 3.0,
                    "base_clearance_mm": max(2.0, 0.6 * wall),
                    "opening_clearance_mm": max(2.0, 0.6 * wall),
                    "ignored_pairs": [list(pair) for pair in ignored_pairs],
                },
                "feature_manufacturability": {
                    "minimum_feature_mm": manufacturing.minimum_feature_mm,
                    "minimum_relief_depth_mm": minimum_relief_depth_mm,
                    "maximum_relief_depth_mm": maximum_depth,
                    "minimum_blend_mm": minimum_blend_mm,
                    "wall_reserve_mm": max(0.5, wall - maximum_depth),
                },
                "templates": templates,
                "roots": roots,
            },
            "output": {
                "directory": (
                    "outputs/product_generators/design_interpreter/"
                    f"{motor_id}"
                ),
                "basename": motor_id,
                "max_generation_seconds": 30.0,
            },
        }
        report = SemanticCompilationReport(
            compiler_version=COMPILER_VERSION,
            source_program_id=program.id,
            output_program_id=motor_id,
            feature_traces=tuple(traces),
            compiled_relations=len(program.relations),
            ignored_overlap_pairs=ignored_pairs,
        )
        report.validate(len(program.features))
        return SemanticCompilationResult(motor_program=motor_program, report=report)

    @staticmethod
    def _voxel_size(width: float, depth: float, height: float) -> float:
        return float(min(1.0, max(0.55, max(width, depth, height) / 180.0)))

    @staticmethod
    def _body_fields(program: DesignSemanticProgram) -> list[dict[str, Any]]:
        body = program.body
        width_radius = 0.5 * body.width_mm
        depth_radius = 0.5 * body.depth_mm
        height_radius = 0.46 * body.height_mm
        front_factor = 0.88 if body.family in {"character", "organic"} else 0.96
        return [
            {
                "id": "body",
                "center": [0.0, 0.0, 0.0],
                "radii": [width_radius, depth_radius, height_radius],
            },
            {
                "id": "front_mass",
                "center": [0.0, -0.16 * body.depth_mm, 0.02 * body.height_mm],
                "radii": [
                    front_factor * width_radius,
                    0.78 * depth_radius,
                    0.88 * height_radius,
                ],
            },
        ]

    @staticmethod
    def _compile_anchor(
        anchor: SemanticAnchor, feature: FeatureIntent
    ) -> dict[str, float]:
        region_center = {
            "front": 0.0,
            "back": 180.0,
            "left": -90.0,
            "right": 90.0,
            "upper": 0.0,
            "lower": 0.0,
            "all_around": 0.0,
        }[anchor.region]
        horizontal_span = 180.0 if anchor.region == "all_around" else 60.0
        height = anchor.vertical
        if anchor.region == "upper":
            height = min(max(height, 0.72), 0.84)
        elif anchor.region == "lower":
            height = min(height, 0.35)
        return {
            "azimuth_degrees": region_center + anchor.horizontal * horizontal_span,
            "height_ratio": height,
            "offset_mm": 0.15 * feature.size.depth_mm
            if feature.surface_effect in {"raised", "marking"}
            else 0.0,
            "roll_degrees": anchor.roll_degrees,
        }

    @classmethod
    def _compile_feature(
        cls,
        feature: FeatureIntent,
        *,
        template_id: str,
        body_width_mm: float,
        body_height_mm: float,
        minimum_feature_mm: float,
        minimum_blend_mm: float,
        minimum_relief_depth_mm: float,
        maximum_relief_depth_mm: float,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        width = max(
            feature.size.width_ratio * body_width_mm,
            minimum_feature_mm,
        )
        height = max(
            feature.size.height_ratio * body_height_mm,
            minimum_feature_mm,
        )
        depth = feature.size.depth_mm
        operation = (
            "subtract"
            if feature.surface_effect in {"recessed", "cutout"}
            else "add"
        )
        minimum_compiled_blend = max(0.5, 0.5 * minimum_feature_mm)
        blend = max(
            minimum_compiled_blend,
            min(width, height, depth) * 0.35,
        )
        base: dict[str, Any] = {
            "id": template_id,
            "operation": operation,
            "blend_mm": blend,
            "probe": [0.0, 0.0, 0.0],
        }
        transform = None
        if feature.form_hint in {"slit", "capsule"}:
            requested_radius = max(
                0.5 * height,
                0.5 * minimum_feature_mm,
            )
            # A capsule requires distinct start/end points. Semantic inputs can
            # legitimately describe a square or vertical "slit" (for example,
            # a stylized eye), where height >= width. Capping the radius below
            # half the width preserves a real center segment instead of
            # emitting a degenerate capsule rejected by the Motor contract.
            radius = min(requested_radius, 0.45 * width)
            half_segment = max(0.0, 0.5 * width - radius)
            base.update(
                kind="capsule",
                start=[-half_segment, 0.0, 0.0],
                end=[half_segment, 0.0, 0.0],
                radius_mm=radius,
            )
            effective_depth = min(
                maximum_relief_depth_mm,
                max(depth, 1.01 * minimum_relief_depth_mm),
            )
            transform = {
                "scale": [1.0, effective_depth / radius, 1.0],
            }
            # Manufacturability evaluates the blend after applying the node
            # transform. Reserve enough nominal blend for a shallow capsule so
            # its effective blend still satisfies the Motor contract.
            depth_scale = min(1.0, effective_depth / radius)
            base["blend_mm"] = max(
                float(base["blend_mm"]),
                1.01 * minimum_blend_mm / depth_scale,
            )
        elif feature.form_hint in {"disc", "oval"}:
            base.update(
                kind="ellipsoid",
                center=[0.0, 0.0, 0.0],
                radii=[0.5 * width, depth, 0.5 * height],
            )
        elif feature.form_hint in {"leaf", "point"}:
            base.update(
                kind="rounded_triangle_prism",
                vertices_xz=[
                    [-0.5 * width, -0.5 * height],
                    [0.5 * width, -0.5 * height],
                    [0.0, 0.5 * height],
                ],
                half_depth_mm=depth,
                round_mm=max(0.4, 0.25 * minimum_feature_mm),
            )
        elif feature.form_hint == "arch":
            base.update(
                kind="arched_prism",
                center=[0.0, 0.0, 0.0],
                bottom_z_mm=-0.5 * height,
                spring_z_mm=0.05 * height,
                half_width_mm=0.5 * width,
                half_depth_mm=depth,
                round_mm=max(0.4, 0.25 * minimum_feature_mm),
            )
        else:
            base.update(
                kind="rounded_box",
                center=[0.0, 0.0, 0.0],
                half_sizes=[0.5 * width, depth, 0.5 * height],
                round_mm=max(0.4, min(width, height) * 0.12),
            )
        return base, transform

    @staticmethod
    def _mesh_quality() -> dict[str, Any]:
        return {
            "subdivision_passes": 1,
            "projection_iterations": 3,
            "projection_epsilon_mm": 0.07,
            "max_surface_error_mm": 0.015,
            "iterations": 4,
            "lambda_factor": 0.42,
            "mu_factor": -0.44,
            "rim_axial_band_mm": 13.0,
            "rim_radial_band": 0.7,
            "max_displacement_mm": 0.8,
            "base_protection_mm": 1.2,
            "drain_protection_mm": 1.6,
            "max_volume_drift_percent": 0.8,
            "minimum_roughness_improvement_percent": 1.0,
        }
