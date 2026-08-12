from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .specification import _object, _vector3
from .vessel_specification import OrganicVesselParser, OrganicVesselSpecification


SUPPORTED_FEATURE_KINDS = frozenset(
    {
        "ellipsoid",
        "capsule",
        "rounded_box",
        "cylinder",
        "rounded_triangle_prism",
        "arched_prism",
    }
)


def _optional_vector3(data: dict[str, Any], key: str):
    value = data.get(key)
    return _vector3(value, f"features[].{key}") if value is not None else None


@dataclass(frozen=True, slots=True)
class FeatureInstruction:
    id: str
    operation: str
    kind: str
    probe: tuple[float, float, float]
    blend_mm: float
    center: tuple[float, float, float] | None = None
    radii: tuple[float, float, float] | None = None
    start: tuple[float, float, float] | None = None
    end: tuple[float, float, float] | None = None
    radius_mm: float | None = None
    half_height_mm: float | None = None
    half_sizes: tuple[float, float, float] | None = None
    round_mm: float | None = None
    vertices_xz: tuple[tuple[float, float], ...] | None = None
    center_y_mm: float | None = None
    half_depth_mm: float | None = None
    bottom_z_mm: float | None = None
    spring_z_mm: float | None = None
    half_width_mm: float | None = None

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("Feature instruction id must not be empty.")
        if self.operation not in {"add", "subtract"}:
            raise ValueError(f"Unsupported feature operation '{self.operation}'.")
        if self.kind not in SUPPORTED_FEATURE_KINDS:
            raise ValueError(f"Unsupported feature kind '{self.kind}'.")
        if self.blend_mm <= 0.0:
            raise ValueError("Feature blend_mm must be positive.")
        if self.kind == "ellipsoid":
            if self.center is None or self.radii is None:
                raise ValueError("ellipsoid requires center and radii.")
            if any(value <= 0.0 for value in self.radii):
                raise ValueError("ellipsoid radii must be positive.")
        elif self.kind == "capsule":
            if self.start is None or self.end is None or self.radius_mm is None:
                raise ValueError("capsule requires start, end and radius_mm.")
            if self.start == self.end or self.radius_mm <= 0.0:
                raise ValueError("capsule dimensions are invalid.")
        elif self.kind == "rounded_box":
            if self.center is None or self.half_sizes is None or self.round_mm is None:
                raise ValueError("rounded_box requires center, half_sizes and round_mm.")
            if any(value <= 0.0 for value in self.half_sizes):
                raise ValueError("rounded_box half_sizes must be positive.")
            if not 0.0 < self.round_mm < min(self.half_sizes):
                raise ValueError("rounded_box round_mm must fit inside half_sizes.")
        elif self.kind == "cylinder":
            if self.center is None or self.radius_mm is None or self.half_height_mm is None:
                raise ValueError("cylinder requires center, radius_mm and half_height_mm.")
            if min(self.radius_mm, self.half_height_mm) <= 0.0:
                raise ValueError("cylinder dimensions must be positive.")
        elif self.kind == "rounded_triangle_prism":
            if (
                self.vertices_xz is None
                or self.center_y_mm is None
                or self.half_depth_mm is None
                or self.round_mm is None
            ):
                raise ValueError("rounded_triangle_prism dimensions are incomplete.")
            if len(self.vertices_xz) != 3:
                raise ValueError("rounded_triangle_prism requires three vertices_xz.")
            if min(self.half_depth_mm, self.round_mm) <= 0.0:
                raise ValueError("rounded_triangle_prism dimensions must be positive.")
        else:
            required = (
                self.center,
                self.bottom_z_mm,
                self.spring_z_mm,
                self.half_width_mm,
                self.half_depth_mm,
                self.round_mm,
            )
            if any(value is None for value in required):
                raise ValueError("arched_prism dimensions are incomplete.")
            if self.spring_z_mm <= self.bottom_z_mm:
                raise ValueError("arched_prism spring must be above its bottom.")
            if min(self.half_width_mm, self.half_depth_mm, self.round_mm) <= 0.0:
                raise ValueError("arched_prism dimensions must be positive.")


@dataclass(frozen=True, slots=True)
class FeatureProgramSpecification:
    vessel_specification: OrganicVesselSpecification
    features: tuple[FeatureInstruction, ...]

    def __getattr__(self, name: str):
        return getattr(self.vessel_specification, name)

    def validate(self) -> None:
        self.vessel_specification.validate()
        if not self.features:
            raise ValueError("Feature program requires at least one instruction.")
        identifiers: set[str] = set()
        for feature in self.features:
            feature.validate()
            if feature.id in identifiers:
                raise ValueError(f"Duplicate feature id '{feature.id}'.")
            identifiers.add(feature.id)
            if any(
                feature.probe[axis] <= self.grid.minimum[axis]
                or feature.probe[axis] >= self.grid.maximum[axis]
                for axis in range(3)
            ):
                raise ValueError(f"Feature probe '{feature.id}' lies outside the grid.")


class FeatureProgramParser:
    def parse_file(self, path: str | Path) -> FeatureProgramSpecification:
        source = Path(path).resolve()
        return self.parse_dict(json.loads(source.read_text(encoding="utf-8")))

    def parse_dict(self, data: dict[str, Any]) -> FeatureProgramSpecification:
        vessel = OrganicVesselParser().parse_dict(data)
        program = _object(data, "feature_program")
        raw_features = program.get("features")
        if not isinstance(raw_features, list) or not all(
            isinstance(item, dict) for item in raw_features
        ):
            raise TypeError("feature_program.features must be an array of objects.")
        specification = FeatureProgramSpecification(
            vessel_specification=vessel,
            features=tuple(self._feature(item) for item in raw_features),
        )
        specification.validate()
        return specification

    @staticmethod
    def _feature(data: dict[str, Any]) -> FeatureInstruction:
        raw_vertices = data.get("vertices_xz")
        vertices = None
        if raw_vertices is not None:
            if not isinstance(raw_vertices, list) or len(raw_vertices) != 3:
                raise TypeError("features[].vertices_xz must contain three points.")
            vertices = tuple((float(point[0]), float(point[1])) for point in raw_vertices)
        return FeatureInstruction(
            id=str(data["id"]),
            operation=str(data["operation"]),
            kind=str(data["kind"]),
            probe=_vector3(data["probe"], "features[].probe"),
            blend_mm=float(data.get("blend_mm", 1.0)),
            center=_optional_vector3(data, "center"),
            radii=_optional_vector3(data, "radii"),
            start=_optional_vector3(data, "start"),
            end=_optional_vector3(data, "end"),
            radius_mm=float(data["radius_mm"]) if "radius_mm" in data else None,
            half_height_mm=(
                float(data["half_height_mm"]) if "half_height_mm" in data else None
            ),
            half_sizes=_optional_vector3(data, "half_sizes"),
            round_mm=float(data["round_mm"]) if "round_mm" in data else None,
            vertices_xz=vertices,
            center_y_mm=(
                float(data["center_y_mm"]) if "center_y_mm" in data else None
            ),
            half_depth_mm=(
                float(data["half_depth_mm"]) if "half_depth_mm" in data else None
            ),
            bottom_z_mm=(
                float(data["bottom_z_mm"]) if "bottom_z_mm" in data else None
            ),
            spring_z_mm=(
                float(data["spring_z_mm"]) if "spring_z_mm" in data else None
            ),
            half_width_mm=(
                float(data["half_width_mm"]) if "half_width_mm" in data else None
            ),
        )
