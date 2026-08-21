from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .mesh_quality import OrganicMeshQualityContract
from .specification import (
    ImplicitFieldSpec,
    OrganicBounds,
    OrganicOutputSpec,
    SmoothUnionSpec,
    _field,
    _object,
    _vector3,
)


@dataclass(frozen=True, slots=True)
class OrganicVesselContract:
    wall_mm: float
    base_z_mm: float
    cavity_floor_z_mm: float
    opening_center: tuple[float, float]
    opening_radii: tuple[float, float]
    opening_start_z_mm: float
    opening_blend_mm: float
    rim_round_mm: float
    drain_center: tuple[float, float]
    drain_radius_mm: float
    drain_start_z_mm: float
    drain_end_z_mm: float
    shell_field_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.wall_mm <= 0.0:
            raise ValueError("vessel.wall_mm must be positive.")
        if self.cavity_floor_z_mm <= self.base_z_mm:
            raise ValueError("Cavity floor must be above the flat base.")
        if any(radius <= 0.0 for radius in self.opening_radii):
            raise ValueError("Opening radii must be positive.")
        if self.opening_start_z_mm <= self.cavity_floor_z_mm:
            raise ValueError("Opening transition must start above cavity floor.")
        if self.opening_blend_mm <= 0.0:
            raise ValueError("Opening blend must be positive.")
        if self.rim_round_mm <= 0.0:
            raise ValueError("Rim round radius must be positive.")
        if self.drain_radius_mm <= 0.0:
            raise ValueError("Drain radius must be positive.")
        if self.drain_start_z_mm >= self.base_z_mm:
            raise ValueError("Drain must begin below the flat base.")
        if self.drain_end_z_mm <= self.cavity_floor_z_mm:
            raise ValueError("Drain must overlap the cavity above its floor.")
        if self.drain_start_z_mm >= self.drain_end_z_mm:
            raise ValueError("Drain start must be below drain end.")
        if len(set(self.shell_field_ids)) != len(self.shell_field_ids):
            raise ValueError("vessel.shell_field_ids must be unique.")

    @property
    def bottom_mm(self) -> float:
        return self.cavity_floor_z_mm - self.base_z_mm


@dataclass(frozen=True, slots=True)
class OrganicVesselSpecification:
    id: str
    grid: OrganicBounds
    fields: tuple[ImplicitFieldSpec, ...]
    composition: SmoothUnionSpec
    vessel: OrganicVesselContract
    mesh_quality: OrganicMeshQualityContract | None
    output: OrganicOutputSpec

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("id must not be empty.")
        self.grid.validate()
        self.composition.validate()
        self.vessel.validate()
        if self.mesh_quality is not None:
            self.mesh_quality.validate()
        self.output.validate()
        if len(self.fields) < 2:
            raise ValueError("Organic vessel requires at least two envelope fields.")
        ids: set[str] = set()
        for field in self.fields:
            field.validate()
            if field.id in ids:
                raise ValueError(f"Duplicate organic field id '{field.id}'.")
            ids.add(field.id)
        unknown = set(self.composition.field_ids) - ids
        if unknown:
            raise ValueError(f"Unknown composition fields: {sorted(unknown)}")
        unknown_shell = set(self.vessel.shell_field_ids) - ids
        if unknown_shell:
            raise ValueError(
                f"Unknown vessel shell fields: {sorted(unknown_shell)}"
            )
        if self.vessel.bottom_mm < self.grid.voxel_mm * 3.0:
            raise ValueError("Vessel bottom must span at least three voxels.")
        if self.vessel.wall_mm < self.grid.voxel_mm * 3.0:
            raise ValueError("Vessel wall must span at least three voxels.")


class OrganicVesselParser:
    def parse_file(self, path: str | Path) -> OrganicVesselSpecification:
        source = Path(path).resolve()
        return self.parse_dict(json.loads(source.read_text(encoding="utf-8")))

    def parse_dict(self, data: dict[str, Any]) -> OrganicVesselSpecification:
        if not isinstance(data, dict):
            raise TypeError("Organic vessel specification must be an object.")
        grid = _object(data, "grid")
        composition = _object(data, "composition")
        vessel = _object(data, "vessel")
        output = _object(data, "output")
        mesh_quality_data = data.get("mesh_quality")
        if mesh_quality_data is not None and not isinstance(mesh_quality_data, dict):
            raise TypeError("mesh_quality must be an object when provided.")
        fields = data.get("fields")
        if not isinstance(fields, list) or not all(isinstance(item, dict) for item in fields):
            raise TypeError("fields must be an array of objects.")
        field_ids = composition.get("field_ids")
        if not isinstance(field_ids, list) or not all(isinstance(item, str) for item in field_ids):
            raise TypeError("composition.field_ids must be an array of strings.")

        opening_center = _vector2(vessel["opening_center"], "vessel.opening_center")
        opening_radii = _vector2(vessel["opening_radii"], "vessel.opening_radii")
        drain_center = _vector2(vessel["drain_center"], "vessel.drain_center")
        specification = OrganicVesselSpecification(
            id=str(data.get("id", "organic_vessel")),
            grid=OrganicBounds(
                minimum=_vector3(grid["minimum"], "grid.minimum"),
                maximum=_vector3(grid["maximum"], "grid.maximum"),
                voxel_mm=float(grid["voxel_mm"]),
            ),
            fields=tuple(_field(item) for item in fields),
            composition=SmoothUnionSpec(
                field_ids=tuple(field_ids),
                blend_mm=float(composition["blend_mm"]),
            ),
            vessel=OrganicVesselContract(
                wall_mm=float(vessel["wall_mm"]),
                base_z_mm=float(vessel["base_z_mm"]),
                cavity_floor_z_mm=float(vessel["cavity_floor_z_mm"]),
                opening_center=opening_center,
                opening_radii=opening_radii,
                opening_start_z_mm=float(vessel["opening_start_z_mm"]),
                opening_blend_mm=float(vessel["opening_blend_mm"]),
                rim_round_mm=float(vessel["rim_round_mm"]),
                drain_center=drain_center,
                drain_radius_mm=float(vessel["drain_radius_mm"]),
                drain_start_z_mm=float(vessel["drain_start_z_mm"]),
                drain_end_z_mm=float(vessel["drain_end_z_mm"]),
                shell_field_ids=tuple(
                    str(field_id)
                    for field_id in vessel.get("shell_field_ids", [])
                ),
            ),
            mesh_quality=(
                OrganicMeshQualityContract(
                    subdivision_passes=int(mesh_quality_data["subdivision_passes"]),
                    projection_iterations=int(
                        mesh_quality_data["projection_iterations"]
                    ),
                    projection_epsilon_mm=float(
                        mesh_quality_data["projection_epsilon_mm"]
                    ),
                    max_surface_error_mm=float(
                        mesh_quality_data["max_surface_error_mm"]
                    ),
                    iterations=int(mesh_quality_data["iterations"]),
                    lambda_factor=float(mesh_quality_data["lambda_factor"]),
                    mu_factor=float(mesh_quality_data["mu_factor"]),
                    rim_axial_band_mm=float(mesh_quality_data["rim_axial_band_mm"]),
                    rim_radial_band=float(mesh_quality_data["rim_radial_band"]),
                    max_displacement_mm=float(
                        mesh_quality_data["max_displacement_mm"]
                    ),
                    base_protection_mm=float(
                        mesh_quality_data["base_protection_mm"]
                    ),
                    drain_protection_mm=float(
                        mesh_quality_data["drain_protection_mm"]
                    ),
                    max_volume_drift_percent=float(
                        mesh_quality_data["max_volume_drift_percent"]
                    ),
                    minimum_roughness_improvement_percent=float(
                        mesh_quality_data[
                            "minimum_roughness_improvement_percent"
                        ]
                    ),
                )
                if mesh_quality_data is not None
                else None
            ),
            output=OrganicOutputSpec(
                directory=Path(str(output["directory"])),
                basename=str(output["basename"]),
                max_generation_seconds=float(output["max_generation_seconds"]),
            ),
        )
        specification.validate()
        return specification


def _vector2(value: Any, name: str) -> tuple[float, float]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
    ):
        raise TypeError(f"{name} must contain two numeric values.")
    return (float(value[0]), float(value[1]))
