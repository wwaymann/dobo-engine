from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .specification import _object, _vector3
from .vessel_specification import OrganicVesselParser, OrganicVesselSpecification


@dataclass(frozen=True, slots=True)
class StructuralPrimitiveSpec:
    id: str
    kind: str
    center: tuple[float, float, float]
    half_sizes: tuple[float, float, float] | None
    radius_mm: float | None
    half_height_mm: float | None
    round_mm: float | None
    blend_mm: float

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("Structural primitive id must not be empty.")
        if self.kind not in {"rounded_box", "cylinder"}:
            raise ValueError(f"Unsupported structural primitive kind '{self.kind}'.")
        if self.blend_mm <= 0.0:
            raise ValueError("Structural primitive blend_mm must be positive.")
        if self.kind == "rounded_box":
            if self.half_sizes is None or self.round_mm is None:
                raise ValueError("rounded_box requires half_sizes and round_mm.")
            if any(value <= 0.0 for value in self.half_sizes):
                raise ValueError("rounded_box half_sizes must be positive.")
            if not 0.0 < self.round_mm < min(self.half_sizes):
                raise ValueError("rounded_box round_mm must fit inside half_sizes.")
        if self.kind == "cylinder":
            if self.radius_mm is None or self.half_height_mm is None:
                raise ValueError("cylinder requires radius_mm and half_height_mm.")
            if self.radius_mm <= 0.0 or self.half_height_mm <= 0.0:
                raise ValueError("cylinder dimensions must be positive.")


@dataclass(frozen=True, slots=True)
class StructuralCutoutSpec:
    id: str
    kind: str
    center: tuple[float, float, float]
    half_sizes: tuple[float, float, float] | None
    round_mm: float | None
    start: tuple[float, float, float] | None
    end: tuple[float, float, float] | None
    radius_mm: float | None
    bottom_z_mm: float | None
    spring_z_mm: float | None
    half_width_mm: float | None
    half_depth_mm: float | None
    blend_mm: float

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("Structural cutout id must not be empty.")
        if self.kind not in {"rounded_box", "capsule", "arched_prism"}:
            raise ValueError(f"Unsupported structural cutout kind '{self.kind}'.")
        if self.blend_mm <= 0.0:
            raise ValueError("Structural cutout blend_mm must be positive.")
        if self.kind == "rounded_box":
            if self.half_sizes is None or self.round_mm is None:
                raise ValueError("rounded_box cutout requires half_sizes and round_mm.")
        if self.kind == "capsule":
            if self.start is None or self.end is None or self.radius_mm is None:
                raise ValueError("capsule cutout requires start, end and radius_mm.")
            if self.radius_mm <= 0.0 or self.start == self.end:
                raise ValueError("capsule cutout dimensions are invalid.")
        if self.kind == "arched_prism":
            required = (
                self.bottom_z_mm,
                self.spring_z_mm,
                self.half_width_mm,
                self.half_depth_mm,
                self.round_mm,
            )
            if any(value is None for value in required):
                raise ValueError("arched_prism cutout dimensions are incomplete.")
            if self.spring_z_mm <= self.bottom_z_mm:
                raise ValueError("arched_prism spring must be above its bottom.")
            if min(self.half_width_mm, self.half_depth_mm, self.round_mm) <= 0.0:
                raise ValueError("arched_prism dimensions must be positive.")


@dataclass(frozen=True, slots=True)
class StructuralCompositionContract:
    additions: tuple[StructuralPrimitiveSpec, ...]
    cutouts: tuple[StructuralCutoutSpec, ...]

    def validate(self) -> None:
        if not self.additions:
            raise ValueError("Structural composition requires additions.")
        identifiers: set[str] = set()
        for primitive in (*self.additions, *self.cutouts):
            primitive.validate()
            if primitive.id in identifiers:
                raise ValueError(f"Duplicate structural id '{primitive.id}'.")
            identifiers.add(primitive.id)


@dataclass(frozen=True, slots=True)
class StructuralVesselSpecification:
    vessel_specification: OrganicVesselSpecification
    structure: StructuralCompositionContract

    def __getattr__(self, name: str):
        return getattr(self.vessel_specification, name)

    def validate(self) -> None:
        self.vessel_specification.validate()
        self.structure.validate()
        clearance = 2.0 * self.grid.voxel_mm
        for primitive in self.structure.additions:
            if primitive.kind == "rounded_box":
                extent = primitive.half_sizes
            else:
                extent = (
                    primitive.radius_mm,
                    primitive.radius_mm,
                    primitive.half_height_mm,
                )
            for axis in range(3):
                if (
                    primitive.center[axis] - extent[axis]
                    <= self.grid.minimum[axis] + clearance
                    or primitive.center[axis] + extent[axis]
                    >= self.grid.maximum[axis] - clearance
                ):
                    raise ValueError(
                        f"Structural addition '{primitive.id}' requires more grid clearance."
                    )


class StructuralVesselParser:
    def parse_file(self, path: str | Path) -> StructuralVesselSpecification:
        source = Path(path).resolve()
        return self.parse_dict(json.loads(source.read_text(encoding="utf-8")))

    def parse_dict(self, data: dict[str, Any]) -> StructuralVesselSpecification:
        vessel = OrganicVesselParser().parse_dict(data)
        structure = _object(data, "structure")
        additions = structure.get("additions")
        cutouts = structure.get("cutouts", [])
        if not isinstance(additions, list) or not all(
            isinstance(item, dict) for item in additions
        ):
            raise TypeError("structure.additions must be an array of objects.")
        if not isinstance(cutouts, list) or not all(
            isinstance(item, dict) for item in cutouts
        ):
            raise TypeError("structure.cutouts must be an array of objects.")
        specification = StructuralVesselSpecification(
            vessel_specification=vessel,
            structure=StructuralCompositionContract(
                additions=tuple(self._addition(item) for item in additions),
                cutouts=tuple(self._cutout(item) for item in cutouts),
            ),
        )
        specification.validate()
        return specification

    @staticmethod
    def _addition(data: dict[str, Any]) -> StructuralPrimitiveSpec:
        kind = str(data["kind"])
        half_sizes = data.get("half_sizes")
        return StructuralPrimitiveSpec(
            id=str(data["id"]),
            kind=kind,
            center=_vector3(data["center"], "structure.additions[].center"),
            half_sizes=(
                _vector3(half_sizes, "structure.additions[].half_sizes")
                if half_sizes is not None
                else None
            ),
            radius_mm=(float(data["radius_mm"]) if "radius_mm" in data else None),
            half_height_mm=(
                float(data["half_height_mm"])
                if "half_height_mm" in data
                else None
            ),
            round_mm=(float(data["round_mm"]) if "round_mm" in data else None),
            blend_mm=float(data.get("blend_mm", 1.0)),
        )

    @staticmethod
    def _cutout(data: dict[str, Any]) -> StructuralCutoutSpec:
        half_sizes = data.get("half_sizes")
        start = data.get("start")
        end = data.get("end")
        return StructuralCutoutSpec(
            id=str(data["id"]),
            kind=str(data["kind"]),
            center=_vector3(data["center"], "structure.cutouts[].center"),
            half_sizes=(
                _vector3(half_sizes, "structure.cutouts[].half_sizes")
                if half_sizes is not None
                else None
            ),
            round_mm=(float(data["round_mm"]) if "round_mm" in data else None),
            start=(
                _vector3(start, "structure.cutouts[].start")
                if start is not None
                else None
            ),
            end=(
                _vector3(end, "structure.cutouts[].end")
                if end is not None
                else None
            ),
            radius_mm=(float(data["radius_mm"]) if "radius_mm" in data else None),
            bottom_z_mm=(
                float(data["bottom_z_mm"]) if "bottom_z_mm" in data else None
            ),
            spring_z_mm=(
                float(data["spring_z_mm"]) if "spring_z_mm" in data else None
            ),
            half_width_mm=(
                float(data["half_width_mm"]) if "half_width_mm" in data else None
            ),
            half_depth_mm=(
                float(data["half_depth_mm"]) if "half_depth_mm" in data else None
            ),
            blend_mm=float(data.get("blend_mm", 1.0)),
        )
