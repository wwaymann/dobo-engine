from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True, slots=True)
class ProportionalScaleContract:
    reference_radius_mm: float
    reference_height_mm: float
    minimum_scale: float
    maximum_scale: float
    scale_depth: bool = False

    def validate(self) -> None:
        if min(self.reference_radius_mm, self.reference_height_mm) <= 0.0:
            raise ValueError("Proportional-scale references must be positive.")
        if not 0.0 < self.minimum_scale <= 1.0 <= self.maximum_scale:
            raise ValueError(
                "Proportional-scale limits must enclose the neutral scale 1.0."
            )

    def factors(
        self,
        *,
        radial_distance_mm: float,
        usable_height_mm: float,
    ) -> tuple[float, float, float]:
        tangent = float(
            np.clip(
                radial_distance_mm / self.reference_radius_mm,
                self.minimum_scale,
                self.maximum_scale,
            )
        )
        vertical = float(
            np.clip(
                usable_height_mm / self.reference_height_mm,
                self.minimum_scale,
                self.maximum_scale,
            )
        )
        depth = sqrt(tangent * vertical) if self.scale_depth else 1.0
        return tangent, depth, vertical


@dataclass(frozen=True, slots=True)
class LayoutConstraintContract:
    minimum_clearance_mm: float
    base_clearance_mm: float
    opening_clearance_mm: float
    ignored_pairs: tuple[tuple[str, str], ...] = ()

    def validate(self) -> None:
        if min(
            self.minimum_clearance_mm,
            self.base_clearance_mm,
            self.opening_clearance_mm,
        ) < 0.0:
            raise ValueError("Layout clearances cannot be negative.")
        normalized = [tuple(sorted(pair)) for pair in self.ignored_pairs]
        if any(len(pair) != 2 or not all(pair) for pair in normalized):
            raise ValueError("Every ignored layout pair must name two nodes.")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Ignored layout pairs must be unique.")

    def ignores(self, first: str, second: str) -> bool:
        return tuple(sorted((first, second))) in {
            tuple(sorted(pair)) for pair in self.ignored_pairs
        }


@dataclass(frozen=True, slots=True)
class FeatureManufacturabilityContract:
    minimum_feature_mm: float
    minimum_relief_depth_mm: float
    maximum_relief_depth_mm: float
    minimum_blend_mm: float
    wall_reserve_mm: float

    def validate(self) -> None:
        values = (
            self.minimum_feature_mm,
            self.minimum_relief_depth_mm,
            self.maximum_relief_depth_mm,
            self.minimum_blend_mm,
            self.wall_reserve_mm,
        )
        if min(values) <= 0.0:
            raise ValueError("Feature-manufacturability values must be positive.")
        if self.maximum_relief_depth_mm < self.minimum_relief_depth_mm:
            raise ValueError("Maximum relief depth must exceed its minimum.")


@dataclass(frozen=True, slots=True)
class LayoutReport:
    checks: dict[str, bool]
    evaluated_pairs: int
    ignored_pairs: int
    minimum_pair_clearance_mm: float

    def validate(self) -> None:
        failed = [name for name, valid in self.checks.items() if not valid]
        if failed:
            raise RuntimeError(f"Adaptive layout checks failed: {failed}")


@dataclass(frozen=True, slots=True)
class ManufacturabilityReport:
    checks: dict[str, bool]
    minimum_feature_mm: float
    minimum_relief_depth_mm: float
    maximum_relief_depth_mm: float

    def validate(self) -> None:
        failed = [name for name, valid in self.checks.items() if not valid]
        if failed:
            raise RuntimeError(f"Feature manufacturability checks failed: {failed}")


def feature_half_extents(feature: Any) -> np.ndarray:
    if feature.kind == "ellipsoid":
        return np.asarray(feature.radii, dtype=np.float64)
    if feature.kind == "capsule":
        start = np.asarray(feature.start, dtype=np.float64)
        end = np.asarray(feature.end, dtype=np.float64)
        return 0.5 * np.abs(end - start) + float(feature.radius_mm)
    if feature.kind == "rounded_box":
        return np.asarray(feature.half_sizes, dtype=np.float64)
    if feature.kind == "cylinder":
        return np.asarray(
            (feature.radius_mm, feature.radius_mm, feature.half_height_mm),
            dtype=np.float64,
        )
    if feature.kind == "rounded_triangle_prism":
        points = np.asarray(feature.vertices_xz, dtype=np.float64)
        return np.asarray(
            (
                np.max(np.abs(points[:, 0])),
                feature.half_depth_mm,
                np.max(np.abs(points[:, 1])),
            ),
            dtype=np.float64,
        )
    height = max(
        abs(float(feature.bottom_z_mm)),
        abs(float(feature.spring_z_mm)) + float(feature.half_width_mm),
    )
    return np.asarray(
        (feature.half_width_mm, feature.half_depth_mm, height),
        dtype=np.float64,
    )


def feature_depth_mm(feature: Any) -> float:
    if feature.kind == "ellipsoid":
        return float(feature.radii[1])
    if feature.kind == "capsule":
        return float(feature.radius_mm)
    if feature.kind == "rounded_box":
        return float(feature.half_sizes[1])
    if feature.kind == "cylinder":
        return float(feature.half_height_mm)
    return float(feature.half_depth_mm)


def feature_depth_axis(feature: Any) -> int:
    """Return the local matrix axis that carries the relief extrusion."""
    return 2 if feature.kind == "cylinder" else 1


def placement_node_id(placement_id: str) -> str:
    node = placement_id.rsplit("/", 2)[-2]
    return node.split("[", 1)[0].split(".mirror_", 1)[0]


def evaluate_layout(
    placements: Iterable[Any],
    contract: LayoutConstraintContract,
    *,
    base_z_mm: float,
    opening_start_z_mm: float,
    grid_minimum: tuple[float, float, float],
    grid_maximum: tuple[float, float, float],
) -> LayoutReport:
    contract.validate()
    items = tuple(placements)
    geometry = []
    checks: dict[str, bool] = {}
    for placement in items:
        extents = feature_half_extents(placement.feature)
        world_extents = np.abs(placement.matrix[:3, :3]) @ extents
        center = np.asarray(placement.matrix[:3, 3], dtype=np.float64)
        footprint_radius = float(max(world_extents[0], world_extents[2]))
        node_id = placement_node_id(placement.id)
        geometry.append((placement, node_id, center, world_extents, footprint_radius))
        checks[f"{placement.id}/base_clearance"] = (
            center[2] - world_extents[2]
            >= base_z_mm + contract.base_clearance_mm
        )
        checks[f"{placement.id}/opening_clearance"] = (
            center[2] + world_extents[2]
            <= opening_start_z_mm - contract.opening_clearance_mm
        )
        low = center - world_extents
        high = center + world_extents
        checks[f"{placement.id}/inside_grid"] = bool(
            np.all(low >= np.asarray(grid_minimum))
            and np.all(high <= np.asarray(grid_maximum))
        )

    evaluated = 0
    ignored = 0
    clearances: list[float] = []
    for index, first in enumerate(geometry):
        for second in geometry[index + 1 :]:
            if contract.ignores(first[1], second[1]):
                ignored += 1
                continue
            evaluated += 1
            distance = float(np.linalg.norm(first[2] - second[2]))
            clearance = distance - first[4] - second[4]
            clearances.append(clearance)
            name = f"pair/{first[1]}--{second[1]}/clearance"
            checks[name] = clearance >= contract.minimum_clearance_mm
    report = LayoutReport(
        checks=checks,
        evaluated_pairs=evaluated,
        ignored_pairs=ignored,
        minimum_pair_clearance_mm=min(clearances, default=float("inf")),
    )
    return report


def evaluate_manufacturability(
    placements: Iterable[Any],
    contract: FeatureManufacturabilityContract,
    *,
    wall_mm: float,
) -> ManufacturabilityReport:
    contract.validate()
    checks: dict[str, bool] = {}
    feature_sizes: list[float] = []
    relief_depths: list[float] = []
    for placement in placements:
        singular = np.linalg.svd(
            placement.matrix[:3, :3], compute_uv=False
        )
        minimum_scale = float(singular.min())
        extents = feature_half_extents(placement.feature)
        minimum_feature = 2.0 * float(extents.min()) * minimum_scale
        depth_axis = feature_depth_axis(placement.feature)
        depth_scale = float(
            np.linalg.norm(placement.matrix[:3, depth_axis])
        )
        depth = feature_depth_mm(placement.feature) * depth_scale
        blend = float(placement.feature.blend_mm) * minimum_scale
        feature_sizes.append(minimum_feature)
        relief_depths.append(depth)
        prefix = placement.id
        checks[f"{prefix}/minimum_feature"] = (
            minimum_feature >= contract.minimum_feature_mm
        )
        checks[f"{prefix}/minimum_depth"] = (
            depth >= contract.minimum_relief_depth_mm
        )
        checks[f"{prefix}/maximum_depth"] = (
            depth <= contract.maximum_relief_depth_mm
        )
        checks[f"{prefix}/minimum_blend"] = (
            blend >= contract.minimum_blend_mm
        )
        if placement.feature.operation == "subtract":
            checks[f"{prefix}/wall_reserve"] = (
                depth <= wall_mm - contract.wall_reserve_mm
            )
    return ManufacturabilityReport(
        checks=checks,
        minimum_feature_mm=min(feature_sizes),
        minimum_relief_depth_mm=min(relief_depths),
        maximum_relief_depth_mm=max(relief_depths),
    )
