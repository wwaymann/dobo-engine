from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


Vector3 = tuple[float, float, float]


def _vector3(value: Any, name: str) -> Vector3:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
    ):
        raise TypeError(f"{name} must contain three numeric values.")
    return (float(value[0]), float(value[1]), float(value[2]))


@dataclass(frozen=True, slots=True)
class OrganicBounds:
    minimum: Vector3
    maximum: Vector3
    voxel_mm: float

    def validate(self) -> None:
        if self.voxel_mm <= 0.0:
            raise ValueError("grid.voxel_mm must be positive.")
        for minimum, maximum in zip(self.minimum, self.maximum):
            if minimum >= maximum:
                raise ValueError("grid minimum values must be below maximum values.")
            if maximum - minimum < 4.0 * self.voxel_mm:
                raise ValueError("Each grid axis must span at least four voxels.")


@dataclass(frozen=True, slots=True)
class EllipsoidFieldSpec:
    id: str
    center: Vector3
    radii: Vector3

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("fields[].id must not be empty.")
        if any(radius <= 0.0 for radius in self.radii):
            raise ValueError("fields[].radii values must be positive.")


ADVANCED_FIELD_KINDS = frozenset(
    {
        "superellipsoid",
        "faceted_ellipsoid",
        "capped_cylinder",
        "leaf",
        "pointed",
        "lobed_ellipsoid",
        "twisted_faceted",
    }
)


@dataclass(frozen=True, slots=True)
class AdvancedFieldSpec:
    """Reusable non-ellipsoidal implicit field with a common envelope."""

    id: str
    kind: str
    center: Vector3
    radii: Vector3
    exponent: float = 2.0
    sides: int = 6
    rotation_degrees: float = 0.0
    round_mm: float = 0.6

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("fields[].id must not be empty.")
        if self.kind not in ADVANCED_FIELD_KINDS:
            raise ValueError(f"Unsupported advanced field kind '{self.kind}'.")
        if any(radius <= 0.0 for radius in self.radii):
            raise ValueError("fields[].radii values must be positive.")
        if not 1.0 <= self.exponent <= 12.0:
            raise ValueError("Advanced field exponent must be between 1 and 12.")
        if not 3 <= self.sides <= 16:
            raise ValueError("Advanced faceted field sides must be between 3 and 16.")
        if self.round_mm <= 0.0 or self.round_mm >= min(self.radii):
            raise ValueError("Advanced field round_mm must fit inside its radii.")


ImplicitFieldSpec = EllipsoidFieldSpec | AdvancedFieldSpec


@dataclass(frozen=True, slots=True)
class SmoothUnionSpec:
    field_ids: tuple[str, ...]
    blend_mm: float

    def validate(self) -> None:
        if len(self.field_ids) < 2:
            raise ValueError("composition.field_ids requires at least two fields.")
        if len(set(self.field_ids)) != len(self.field_ids):
            raise ValueError("composition.field_ids must be unique.")
        if self.blend_mm <= 0.0:
            raise ValueError("composition.blend_mm must be positive.")


@dataclass(frozen=True, slots=True)
class OrganicOutputSpec:
    directory: Path
    basename: str
    max_generation_seconds: float

    def validate(self) -> None:
        if not self.basename.strip() or Path(self.basename).name != self.basename:
            raise ValueError("output.basename must be a plain filename stem.")
        if Path(self.basename).suffix:
            raise ValueError("output.basename must not contain an extension.")
        if self.max_generation_seconds <= 0.0:
            raise ValueError("output.max_generation_seconds must be positive.")


@dataclass(frozen=True, slots=True)
class OrganicShapeSpecification:
    id: str
    grid: OrganicBounds
    fields: tuple[ImplicitFieldSpec, ...]
    composition: SmoothUnionSpec
    output: OrganicOutputSpec

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("id must not be empty.")
        self.grid.validate()
        self.composition.validate()
        self.output.validate()
        if len(self.fields) < 2:
            raise ValueError("Organic smooth blend requires at least two fields.")
        field_ids: set[str] = set()
        for field in self.fields:
            field.validate()
            if field.id in field_ids:
                raise ValueError(f"Duplicate organic field id '{field.id}'.")
            field_ids.add(field.id)
        unknown = set(self.composition.field_ids) - field_ids
        if unknown:
            raise ValueError(f"Unknown composition fields: {sorted(unknown)}")


class OrganicShapeParser:
    def parse_file(self, path: str | Path) -> OrganicShapeSpecification:
        source = Path(path).resolve()
        return self.parse_dict(json.loads(source.read_text(encoding="utf-8")))

    def parse_dict(self, data: dict[str, Any]) -> OrganicShapeSpecification:
        if not isinstance(data, dict):
            raise TypeError("Organic shape specification must be an object.")
        grid = _object(data, "grid")
        composition = _object(data, "composition")
        output = _object(data, "output")
        fields = data.get("fields")
        if not isinstance(fields, list) or not all(isinstance(item, dict) for item in fields):
            raise TypeError("fields must be an array of objects.")
        field_ids = composition.get("field_ids")
        if not isinstance(field_ids, list) or not all(isinstance(item, str) for item in field_ids):
            raise TypeError("composition.field_ids must be an array of strings.")

        specification = OrganicShapeSpecification(
            id=str(data.get("id", "organic_shape")),
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
            output=OrganicOutputSpec(
                directory=Path(str(output["directory"])),
                basename=str(output["basename"]),
                max_generation_seconds=float(output["max_generation_seconds"]),
            ),
        )
        specification.validate()
        return specification


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a JSON object.")
    return value


def _field(data: dict[str, Any]) -> ImplicitFieldSpec:
    kind = str(data.get("kind", "ellipsoid"))
    common = {
        "id": str(data["id"]),
        "center": _vector3(data["center"], "fields[].center"),
        "radii": _vector3(data["radii"], "fields[].radii"),
    }
    if kind == "ellipsoid":
        return EllipsoidFieldSpec(**common)
    return AdvancedFieldSpec(
        **common,
        kind=kind,
        exponent=float(data.get("exponent", 2.0)),
        sides=int(data.get("sides", 6)),
        rotation_degrees=float(data.get("rotation_degrees", 0.0)),
        round_mm=float(data.get("round_mm", 0.6)),
    )
