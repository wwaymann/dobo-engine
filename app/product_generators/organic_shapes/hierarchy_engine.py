from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import cos, radians, sin

import numpy as np

from .adaptive_refinement import (
    feature_characteristic_size,
    surface_proximity_weights,
)
from .feature_program_engine import FeatureProgramVesselEngine
from .feature_program_specification import FeatureInstruction
from .fields import capped_cylinder_distance, elliptical_column_distance, smooth_intersection, smooth_union
from .hierarchy_specification import HierarchicalFeatureSpecification, HierarchyNode, TransformSpec
from .vessel_engine import OrganicVesselEngine


@dataclass(frozen=True, slots=True)
class PlacedFeature:
    id: str
    feature: FeatureInstruction
    matrix: np.ndarray
    inverse: np.ndarray
    distance_scale: float


def _transform_matrix(transform: TransformSpec) -> np.ndarray:
    rx, ry, rz = (radians(value) for value in transform.rotate_degrees)
    sx, sy, sz = transform.scale
    rotation_x = np.asarray(
        [[1, 0, 0, 0], [0, cos(rx), -sin(rx), 0], [0, sin(rx), cos(rx), 0], [0, 0, 0, 1]],
        dtype=np.float64,
    )
    rotation_y = np.asarray(
        [[cos(ry), 0, sin(ry), 0], [0, 1, 0, 0], [-sin(ry), 0, cos(ry), 0], [0, 0, 0, 1]],
        dtype=np.float64,
    )
    rotation_z = np.asarray(
        [[cos(rz), -sin(rz), 0, 0], [sin(rz), cos(rz), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        dtype=np.float64,
    )
    scale = np.diag([sx, sy, sz, 1.0]).astype(np.float64)
    translation = np.eye(4, dtype=np.float64)
    translation[:3, 3] = transform.translate
    return translation @ rotation_z @ rotation_y @ rotation_x @ scale


class HierarchicalFeatureVesselEngine(OrganicVesselEngine):
    @staticmethod
    def _feature_subdivision_passes(specification) -> int:
        contract = specification.adaptive_refinement
        return contract.detail_subdivision_passes if contract is not None else 0

    @classmethod
    @lru_cache(maxsize=16)
    def placements(
        cls, specification: HierarchicalFeatureSpecification
    ) -> tuple[PlacedFeature, ...]:
        templates = {template.id: template for template in specification.templates}
        placed: list[PlacedFeature] = []

        def visit(node: HierarchyNode, parent: np.ndarray, path: str) -> None:
            node_matrix = _transform_matrix(node.transform)
            mirrors = (None, node.mirror_axis) if node.mirror_axis else (None,)
            for index in range(node.repeat.count):
                step = TransformSpec(
                    translate=tuple(
                        index * value for value in node.repeat.translate_step
                    ),
                    rotate_degrees=tuple(
                        index * value for value in node.repeat.rotate_step_degrees
                    ),
                )
                repeat_matrix = _transform_matrix(step)
                for mirror_axis in mirrors:
                    mirror = np.eye(4, dtype=np.float64)
                    mirror_name = ""
                    if mirror_axis is not None:
                        mirror["xyz".index(mirror_axis), "xyz".index(mirror_axis)] = -1.0
                        mirror_name = f".mirror_{mirror_axis}"
                    world = parent @ mirror @ repeat_matrix @ node_matrix
                    linear = world[:3, :3]
                    distance_scale = float(np.linalg.svd(linear, compute_uv=False).min())
                    instance_path = f"{path}/{node.id}[{index}]{mirror_name}"
                    inverse = np.linalg.inv(world)
                    for template_id in node.template_ids:
                        placed.append(
                            PlacedFeature(
                                id=f"{instance_path}/{template_id}",
                                feature=templates[template_id],
                                matrix=world,
                                inverse=inverse,
                                distance_scale=distance_scale,
                            )
                        )
                    for child in node.children:
                        visit(child, world, instance_path)

        identity = np.eye(4, dtype=np.float64)
        for root in specification.roots:
            visit(root, identity, "root")
        return tuple(placed)

    @staticmethod
    def _local_coordinates(placement: PlacedFeature, x, y, z):
        return (
            placement.inverse[0, 0] * x
            + placement.inverse[0, 1] * y
            + placement.inverse[0, 2] * z
            + placement.inverse[0, 3],
            placement.inverse[1, 0] * x
            + placement.inverse[1, 1] * y
            + placement.inverse[1, 2] * z
            + placement.inverse[1, 3],
            placement.inverse[2, 0] * x
            + placement.inverse[2, 1] * y
            + placement.inverse[2, 2] * z
            + placement.inverse[2, 3],
        )

    @classmethod
    def _placed_field(cls, placement: PlacedFeature, x, y, z):
        local_x, local_y, local_z = cls._local_coordinates(placement, x, y, z)
        return (
            FeatureProgramVesselEngine._feature_field(
                placement.feature, local_x, local_y, local_z
            )
            * placement.distance_scale
        )

    @classmethod
    def _outer_field(cls, specification, x, y, z):
        outer = OrganicVesselEngine._outer_field(specification, x, y, z)
        for placement in cls.placements(specification):
            if placement.feature.operation == "add":
                outer = smooth_union(
                    outer,
                    cls._placed_field(placement, x, y, z),
                    placement.feature.blend_mm * placement.distance_scale,
                )
        return outer

    @classmethod
    def _removal_field(cls, specification, placements, x, y, z):
        removal = cls._placed_field(placements[0], x, y, z)
        for placement in placements[1:]:
            removal = smooth_union(
                removal,
                cls._placed_field(placement, x, y, z),
                placement.feature.blend_mm * placement.distance_scale,
            )
        return removal

    @classmethod
    def _material_field(cls, specification, x, y, z):
        vessel = specification.vessel
        base_outer = OrganicVesselEngine._outer_field(specification, x, y, z)
        featured_outer = cls._outer_field(specification, x, y, z)
        offset_cavity = np.maximum(base_outer + vessel.wall_mm, vessel.cavity_floor_z_mm - z)
        opening = np.maximum(
            elliptical_column_distance(x, y, center=vessel.opening_center, radii=vessel.opening_radii),
            vessel.opening_start_z_mm - z,
        )
        cavity = smooth_union(offset_cavity, opening, vessel.opening_blend_mm)
        shell = smooth_intersection(featured_outer, -cavity, vessel.rim_round_mm)
        material = np.maximum(shell, vessel.base_z_mm - z)
        drain_center_z = 0.5 * (vessel.drain_start_z_mm + vessel.drain_end_z_mm)
        drain = capped_cylinder_distance(
            x, y, z,
            center=(vessel.drain_center[0], vessel.drain_center[1], drain_center_z),
            radius=vessel.drain_radius_mm,
            half_height=0.5 * (vessel.drain_end_z_mm - vessel.drain_start_z_mm),
        )
        material = np.maximum(material, -drain)
        subtractors = tuple(
            placement
            for placement in cls.placements(specification)
            if placement.feature.operation == "subtract"
        )
        if subtractors:
            material = np.maximum(
                material,
                -cls._removal_field(specification, subtractors, x, y, z),
            )
        return material

    @classmethod
    def _feature_refinement_weights(cls, specification, vertices):
        contract = specification.adaptive_refinement
        weights = np.zeros(len(vertices), dtype=np.float64)
        if contract is None:
            return weights
        x, y, z = vertices.T
        for placement in cls.placements(specification):
            feature_size = (
                feature_characteristic_size(placement.feature)
                * placement.distance_scale
            )
            band = contract.influence_band_mm(feature_size)
            signed_distance = np.asarray(
                cls._placed_field(placement, x, y, z), dtype=np.float64
            )
            weights = np.maximum(
                weights,
                surface_proximity_weights(
                    signed_distance,
                    band_mm=band,
                    feature_size_mm=feature_size,
                    small_feature_threshold_mm=contract.small_feature_threshold_mm,
                ),
            )
        return weights

    @classmethod
    def adaptive_refinement_diagnostics(cls, specification, mesh):
        contract = specification.adaptive_refinement
        if contract is None:
            raise RuntimeError("Adaptive refinement is not enabled.")
        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        weights = cls._feature_refinement_weights(specification, vertices)
        edges = np.asarray(mesh.edges_unique, dtype=np.int64)
        edge_lengths = np.linalg.norm(
            vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1
        )
        edge_weights = np.max(weights[edges], axis=1)
        feature_edges = edge_weights >= 0.5
        background_edges = edge_weights <= 1e-9
        placements_selected = 0
        small_placements = 0
        x, y, z = vertices.T
        for placement in cls.placements(specification):
            size = (
                feature_characteristic_size(placement.feature)
                * placement.distance_scale
            )
            if size <= contract.small_feature_threshold_mm:
                small_placements += 1
            distance = np.abs(cls._placed_field(placement, x, y, z))
            if np.any(distance <= contract.influence_band_mm(size)):
                placements_selected += 1
        return {
            "placements_selected": placements_selected,
            "small_placements": small_placements,
            "feature_vertices": int(np.count_nonzero(weights >= 0.5)),
            "feature_edges": int(np.count_nonzero(feature_edges)),
            "feature_median_edge_mm": float(np.median(edge_lengths[feature_edges])),
            "background_median_edge_mm": float(
                np.median(edge_lengths[background_edges])
            ),
        }

    @classmethod
    def hierarchy_checks(cls, specification) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        for placement in cls.placements(specification):
            probe = np.asarray((*placement.feature.probe, 1.0), dtype=np.float64)
            world_probe = placement.matrix @ probe
            value = float(
                cls._material_field(
                    specification,
                    np.asarray(world_probe[0]),
                    np.asarray(world_probe[1]),
                    np.asarray(world_probe[2]),
                )
            )
            checks[placement.id] = (
                value < 0.0 if placement.feature.operation == "add" else value > 0.0
            )
        return checks
