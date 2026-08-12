from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
from skimage.measure import marching_cubes
import trimesh

from .fields import ellipsoid_distance, smooth_union
from .specification import OrganicShapeSpecification


@dataclass(frozen=True, slots=True)
class OrganicShapeResult:
    product_id: str
    mesh: trimesh.Trimesh
    stl_path: str
    vertex_count: int
    face_count: int
    component_count: int
    volume_mm3: float
    watertight: bool
    winding_consistent: bool
    stage_seconds: dict[str, float]
    generation_seconds: float
    max_generation_seconds: float

    def validate(self) -> None:
        if self.vertex_count <= 0 or self.face_count <= 0:
            raise RuntimeError("Organic mesh must contain vertices and faces.")
        if self.component_count != 1:
            raise RuntimeError("Organic mesh must contain exactly one component.")
        if self.volume_mm3 <= 0.0:
            raise RuntimeError("Organic mesh volume must be positive.")
        if not self.watertight:
            raise RuntimeError("Organic mesh must be watertight.")
        if not self.winding_consistent:
            raise RuntimeError("Organic mesh winding must be consistent.")


class OrganicShapeEngine:
    def generate(self, specification: OrganicShapeSpecification) -> OrganicShapeResult:
        specification.validate()
        started = perf_counter()
        stages: dict[str, float] = {}

        axes = self._timed(stages, "grid", lambda: self._axes(specification))
        field = self._timed(
            stages,
            "field_composition",
            lambda: self._compose(specification, axes),
        )
        self._validate_boundary(field, specification.grid.voxel_mm)
        mesh = self._timed(
            stages,
            "surface_extraction",
            lambda: self._extract(specification, field),
        )
        self._timed(stages, "mesh_validation", lambda: self._validate_mesh(mesh))

        specification.output.directory.mkdir(parents=True, exist_ok=True)
        stl_path = specification.output.directory / f"{specification.output.basename}.stl"
        self._timed(stages, "stl_export", lambda: mesh.export(str(stl_path)))
        if not stl_path.is_file() or stl_path.stat().st_size <= 0:
            raise RuntimeError("Organic STL export was not created.")

        components = tuple(mesh.split(only_watertight=False))
        result = OrganicShapeResult(
            product_id=specification.id,
            mesh=mesh,
            stl_path=str(stl_path),
            vertex_count=int(len(mesh.vertices)),
            face_count=int(len(mesh.faces)),
            component_count=len(components),
            volume_mm3=float(abs(mesh.volume)),
            watertight=bool(mesh.is_watertight),
            winding_consistent=bool(mesh.is_winding_consistent),
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
    def _axes(specification: OrganicShapeSpecification) -> tuple[np.ndarray, ...]:
        grid = specification.grid
        return tuple(
            np.arange(minimum, maximum + 0.5 * grid.voxel_mm, grid.voxel_mm)
            for minimum, maximum in zip(grid.minimum, grid.maximum)
        )

    @staticmethod
    def _compose(
        specification: OrganicShapeSpecification,
        axes: tuple[np.ndarray, ...],
    ) -> np.ndarray:
        x = axes[0][:, None, None]
        y = axes[1][None, :, None]
        z = axes[2][None, None, :]
        by_id = {field.id: field for field in specification.fields}
        field_ids = specification.composition.field_ids
        composed = ellipsoid_distance(x, y, z, by_id[field_ids[0]])
        for field_id in field_ids[1:]:
            operand = ellipsoid_distance(x, y, z, by_id[field_id])
            composed = smooth_union(
                composed,
                operand,
                specification.composition.blend_mm,
            )
        if not np.isfinite(composed).all():
            raise RuntimeError("Organic field contains non-finite samples.")
        if float(composed.min()) >= 0.0 or float(composed.max()) <= 0.0:
            raise RuntimeError("Organic field does not cross the zero surface.")
        return np.asarray(composed, dtype=np.float32)

    @staticmethod
    def _validate_boundary(field: np.ndarray, voxel_mm: float) -> None:
        boundary_minimum = min(
            float(field[0, :, :].min()),
            float(field[-1, :, :].min()),
            float(field[:, 0, :].min()),
            float(field[:, -1, :].min()),
            float(field[:, :, 0].min()),
            float(field[:, :, -1].min()),
        )
        if boundary_minimum <= voxel_mm:
            raise RuntimeError(
                "Organic surface reaches the sampling boundary; expand grid bounds."
            )

    @staticmethod
    def _extract(
        specification: OrganicShapeSpecification,
        field: np.ndarray,
    ) -> trimesh.Trimesh:
        voxel = specification.grid.voxel_mm
        vertices, faces, normals, _ = marching_cubes(
            field,
            level=0.0,
            spacing=(voxel, voxel, voxel),
            gradient_direction="ascent",
            allow_degenerate=False,
            method="lewiner",
        )
        vertices += np.asarray(specification.grid.minimum, dtype=np.float64)
        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            vertex_normals=normals,
            process=True,
            validate=True,
        )
        mesh.remove_unreferenced_vertices()
        if not mesh.is_winding_consistent or mesh.volume < 0.0:
            mesh.fix_normals(multibody=True)
        return mesh

    @staticmethod
    def _validate_mesh(mesh: trimesh.Trimesh) -> None:
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("Surface extraction must return a Trimesh.")
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            raise RuntimeError("Surface extraction returned an empty mesh.")
        if not mesh.is_watertight:
            raise RuntimeError("Extracted organic mesh is not watertight.")
        if not mesh.is_winding_consistent:
            raise RuntimeError("Extracted organic mesh winding is inconsistent.")
        if len(tuple(mesh.split(only_watertight=False))) != 1:
            raise RuntimeError("Smooth union did not create one connected surface.")
        if abs(float(mesh.volume)) <= 0.0:
            raise RuntimeError("Extracted organic mesh has no volume.")
