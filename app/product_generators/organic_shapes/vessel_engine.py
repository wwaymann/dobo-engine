from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import trimesh

from .engine import OrganicShapeEngine
from .mesh_quality import LocalizedTaubinRefiner, OrganicMeshQualityMetrics
from .fields import (
    capped_cylinder_distance,
    ellipsoid_distance,
    elliptical_column_distance,
    smooth_intersection,
    smooth_union,
)
from .vessel_specification import OrganicVesselSpecification


@dataclass(frozen=True, slots=True)
class OrganicVesselResult:
    product_id: str
    mesh: trimesh.Trimesh
    stl_path: str
    vertex_count: int
    face_count: int
    component_count: int
    volume_mm3: float
    watertight: bool
    winding_consistent: bool
    nominal_wall_mm: float
    bottom_mm: float
    flat_base_z_mm: float
    flat_base_vertex_count: int
    semantic_checks: dict[str, bool]
    mesh_quality: OrganicMeshQualityMetrics | None
    stage_seconds: dict[str, float]
    generation_seconds: float
    max_generation_seconds: float

    def validate(self) -> None:
        if self.vertex_count <= 0 or self.face_count <= 0:
            raise RuntimeError("Organic vessel mesh is empty.")
        if self.component_count != 1:
            raise RuntimeError("Organic vessel must contain one component.")
        if self.volume_mm3 <= 0.0:
            raise RuntimeError("Organic vessel volume must be positive.")
        if not self.watertight or not self.winding_consistent:
            raise RuntimeError("Organic vessel mesh topology is invalid.")
        if self.flat_base_vertex_count < 12:
            raise RuntimeError("Organic vessel has insufficient flat-base support.")
        failed = [name for name, valid in self.semantic_checks.items() if not valid]
        if failed:
            raise RuntimeError(f"Organic vessel semantic checks failed: {failed}")


class OrganicVesselEngine:
    def generate(self, specification: OrganicVesselSpecification) -> OrganicVesselResult:
        specification.validate()
        started = perf_counter()
        stages: dict[str, float] = {}
        axes = self._timed(
            stages,
            "grid",
            lambda: OrganicShapeEngine._axes(specification),
        )
        field = self._timed(
            stages,
            "vessel_field",
            lambda: self._compose_vessel(specification, axes),
        )
        OrganicShapeEngine._validate_boundary(field, specification.grid.voxel_mm)
        semantic_checks = self._timed(
            stages,
            "semantic_validation",
            lambda: self._semantic_checks(specification),
        )
        mesh = self._timed(
            stages,
            "surface_extraction",
            lambda: OrganicShapeEngine._extract(specification, field),
        )
        mesh_quality = None
        if specification.mesh_quality is not None:
            mesh, mesh_quality = self._timed(
                stages,
                "localized_mesh_refinement",
                lambda: LocalizedTaubinRefiner.refine(
                    mesh,
                    specification.mesh_quality,
                    opening_center=specification.vessel.opening_center,
                    opening_radii=specification.vessel.opening_radii,
                    opening_start_z_mm=specification.vessel.opening_start_z_mm,
                    base_z_mm=specification.vessel.base_z_mm,
                    cavity_floor_z_mm=specification.vessel.cavity_floor_z_mm,
                    drain_center=specification.vessel.drain_center,
                    drain_radius_mm=specification.vessel.drain_radius_mm,
                    field_sampler=lambda points: np.asarray(
                        self._material_field(
                            specification,
                            points[:, 0],
                            points[:, 1],
                            points[:, 2],
                        ),
                        dtype=np.float64,
                    ),
                    outer_field_sampler=lambda points: np.asarray(
                        self._outer_field(
                            specification,
                            points[:, 0],
                            points[:, 1],
                            points[:, 2],
                        ),
                        dtype=np.float64,
                    ),
                    feature_weight_sampler=(
                        (lambda vertices: self._feature_refinement_weights(
                            specification,
                            vertices,
                        ))
                        if hasattr(self, "_feature_refinement_weights")
                        else None
                    ),
                ),
            )
            if hasattr(self, "_feature_subdivision_passes"):
                detail_passes = self._feature_subdivision_passes(specification)
                if detail_passes:
                    mesh = self._timed(
                        stages,
                        "adaptive_detail_subdivision",
                        lambda: LocalizedTaubinRefiner.subdivide_feature_detail(
                            mesh,
                            specification.mesh_quality,
                            passes=detail_passes,
                            feature_weight_sampler=lambda vertices: (
                                self._feature_refinement_weights(
                                    specification,
                                    vertices,
                                )
                            ),
                            field_sampler=lambda points: np.asarray(
                                self._material_field(
                                    specification,
                                    points[:, 0],
                                    points[:, 1],
                                    points[:, 2],
                                ),
                                dtype=np.float64,
                            ),
                        ),
                    )
        self._timed(
            stages,
            "mesh_validation",
            lambda: OrganicShapeEngine._validate_mesh(mesh),
        )

        specification.output.directory.mkdir(parents=True, exist_ok=True)
        stl_path = specification.output.directory / f"{specification.output.basename}.stl"
        self._timed(stages, "stl_export", lambda: mesh.export(str(stl_path)))
        if not stl_path.is_file() or stl_path.stat().st_size <= 0:
            raise RuntimeError("Organic vessel STL export was not created.")

        tolerance = 1.25 * specification.grid.voxel_mm
        flat_count = int(
            np.count_nonzero(
                np.abs(mesh.vertices[:, 2] - specification.vessel.base_z_mm)
                <= tolerance
            )
        )
        components = tuple(mesh.split(only_watertight=False))
        result = OrganicVesselResult(
            product_id=specification.id,
            mesh=mesh,
            stl_path=str(stl_path),
            vertex_count=int(len(mesh.vertices)),
            face_count=int(len(mesh.faces)),
            component_count=len(components),
            volume_mm3=float(abs(mesh.volume)),
            watertight=bool(mesh.is_watertight),
            winding_consistent=bool(mesh.is_winding_consistent),
            nominal_wall_mm=specification.vessel.wall_mm,
            bottom_mm=specification.vessel.bottom_mm,
            flat_base_z_mm=specification.vessel.base_z_mm,
            flat_base_vertex_count=flat_count,
            semantic_checks=semantic_checks,
            mesh_quality=mesh_quality,
            stage_seconds=stages,
            generation_seconds=perf_counter() - started,
            max_generation_seconds=specification.output.max_generation_seconds,
        )
        result.validate()
        return result

    @staticmethod
    def _timed(stages: dict[str, float], name: str, operation):
        started = perf_counter()
        result = operation()
        stages[name] = perf_counter() - started
        return result

    @staticmethod
    def _outer_field(specification, x, y, z):
        by_id = {field.id: field for field in specification.fields}
        ids = specification.composition.field_ids
        outer = ellipsoid_distance(x, y, z, by_id[ids[0]])
        for field_id in ids[1:]:
            outer = smooth_union(
                outer,
                ellipsoid_distance(x, y, z, by_id[field_id]),
                specification.composition.blend_mm,
            )
        return outer

    @classmethod
    def _material_field(cls, specification, x, y, z):
        vessel = specification.vessel
        outer = cls._outer_field(specification, x, y, z)

        offset_cavity = np.maximum(
            outer + vessel.wall_mm,
            vessel.cavity_floor_z_mm - z,
        )
        opening = np.maximum(
            elliptical_column_distance(
                x,
                y,
                center=vessel.opening_center,
                radii=vessel.opening_radii,
            ),
            vessel.opening_start_z_mm - z,
        )
        removal = smooth_union(
            offset_cavity,
            opening,
            vessel.opening_blend_mm,
        )
        shell = smooth_intersection(
            outer,
            -removal,
            vessel.rim_round_mm,
        )
        clipped_shell = np.maximum(shell, vessel.base_z_mm - z)

        drain_center_z = 0.5 * (
            vessel.drain_start_z_mm + vessel.drain_end_z_mm
        )
        drain = capped_cylinder_distance(
            x,
            y,
            z,
            center=(vessel.drain_center[0], vessel.drain_center[1], drain_center_z),
            radius=vessel.drain_radius_mm,
            half_height=0.5 * (
                vessel.drain_end_z_mm - vessel.drain_start_z_mm
            ),
        )
        return np.maximum(clipped_shell, -drain)

    @classmethod
    def _compose_vessel(cls, specification, axes):
        x = axes[0][:, None, None]
        y = axes[1][None, :, None]
        z = axes[2][None, None, :]
        field = cls._material_field(specification, x, y, z)
        if not np.isfinite(field).all():
            raise RuntimeError("Organic vessel field contains non-finite samples.")
        if float(field.min()) >= 0.0 or float(field.max()) <= 0.0:
            raise RuntimeError("Organic vessel field does not cross zero.")
        return np.asarray(field, dtype=np.float32)

    @classmethod
    def _semantic_checks(cls, specification) -> dict[str, bool]:
        vessel = specification.vessel

        def sample(x: float, y: float, z: float) -> float:
            value = cls._material_field(
                specification,
                np.asarray(x),
                np.asarray(y),
                np.asarray(z),
            )
            return float(value)

        mid_z = 0.5 * (vessel.cavity_floor_z_mm + vessel.opening_start_z_mm)
        wall_probe_x = max(field.radii[0] for field in specification.fields) - 0.5 * vessel.wall_mm
        base_ring_x = max(vessel.drain_radius_mm + 3.0, 0.25 * wall_probe_x)
        return {
            "outside_is_empty": sample(wall_probe_x + 2.0 * vessel.wall_mm, 0.0, mid_z) > 0.0,
            "wall_is_solid": sample(wall_probe_x, 0.0, mid_z) < 0.0,
            "cavity_is_empty": sample(0.0, 0.0, mid_z) > 0.0,
            "opening_is_clear": sample(
                vessel.opening_center[0],
                vessel.opening_center[1],
                vessel.opening_start_z_mm + 8.0,
            ) > 0.0,
            "base_ring_is_solid": sample(
                base_ring_x,
                0.0,
                vessel.base_z_mm + 0.5 * vessel.bottom_mm,
            ) < 0.0,
            "drain_is_clear": sample(
                vessel.drain_center[0],
                vessel.drain_center[1],
                vessel.base_z_mm + 0.5 * vessel.bottom_mm,
            ) > 0.0,
            "below_base_is_empty": sample(
                base_ring_x,
                0.0,
                vessel.base_z_mm - 2.0 * specification.grid.voxel_mm,
            ) > 0.0,
        }
