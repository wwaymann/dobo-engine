from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PrototypeTextSpec:
    content: str
    size_mm: float
    depth_mm: float
    font: str
    kind: str
    width_fraction: float
    height_fraction: float
    u_center: float
    v_center: float

    def validate(self) -> None:
        if not self.content.strip():
            raise ValueError("texts[].content must not be empty.")
        if self.size_mm <= 0.0 or self.depth_mm <= 0.0:
            raise ValueError("texts[] size_mm and depth_mm must be positive.")
        for name, value in (
            ("width_fraction", self.width_fraction),
            ("height_fraction", self.height_fraction),
            ("u_center", self.u_center),
            ("v_center", self.v_center),
        ):
            if not 0.0 < value < 1.0:
                raise ValueError(f"texts[].{name} must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class PrototypeBodySpec:
    template: str
    color: str
    height_mm: float
    bottom_radius_mm: float
    top_radius_mm: float
    wall_mm: float
    bottom_mm: float

    def validate(self) -> None:
        if self.template != "basic_round_01":
            raise ValueError("body.template must be 'basic_round_01'.")
        for name, value in (
            ("height_mm", self.height_mm),
            ("bottom_radius_mm", self.bottom_radius_mm),
            ("top_radius_mm", self.top_radius_mm),
            ("wall_mm", self.wall_mm),
            ("bottom_mm", self.bottom_mm),
        ):
            if value <= 0.0:
                raise ValueError(f"body.{name} must be positive.")
        if self.wall_mm >= min(self.bottom_radius_mm, self.top_radius_mm):
            raise ValueError("body.wall_mm consumes the planter radius.")
        if self.bottom_mm >= self.height_mm:
            raise ValueError("body.bottom_mm must be below body.height_mm.")


@dataclass(frozen=True, slots=True)
class PrototypeManufacturingSpec:
    process: str
    colors: int
    nozzle_mm: float
    layer_height_mm: float
    max_generation_seconds: float

    def validate(self) -> None:
        if self.process != "fdm":
            raise ValueError("manufacturing.process must be 'fdm'.")
        if self.colors != 1:
            raise ValueError("V2 Prototype 1 must use exactly one color.")
        if self.nozzle_mm <= 0.0 or self.layer_height_mm <= 0.0:
            raise ValueError("Nozzle and layer height must be positive.")
        if self.max_generation_seconds <= 0.0:
            raise ValueError("max_generation_seconds must be positive.")


@dataclass(frozen=True, slots=True)
class PrototypeOutputSpec:
    directory: Path
    basename: str
    mesh_tolerance_mm: float
    angular_tolerance: float

    def validate(self) -> None:
        if not self.basename.strip() or Path(self.basename).name != self.basename:
            raise ValueError("output.basename must be a plain filename stem.")
        if Path(self.basename).suffix:
            raise ValueError("output.basename must not contain an extension.")
        if self.mesh_tolerance_mm <= 0.0 or self.angular_tolerance <= 0.0:
            raise ValueError("Output tolerances must be positive.")


@dataclass(frozen=True, slots=True)
class V2Prototype1Spec:
    id: str
    body: PrototypeBodySpec
    texts: tuple[PrototypeTextSpec, ...]
    manufacturing: PrototypeManufacturingSpec
    output: PrototypeOutputSpec

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("id must not be empty.")
        self.body.validate()
        self.manufacturing.validate()
        self.output.validate()
        if not self.texts:
            raise ValueError("texts must contain at least one item.")
        for text_item in self.texts:
            text_item.validate()
            if text_item.depth_mm < 2.0 * self.manufacturing.layer_height_mm:
                raise ValueError(
                    "texts[].depth_mm must span at least two print layers."
                )


class V2Prototype1Parser:
    def parse_file(self, path: str | Path) -> V2Prototype1Spec:
        source = Path(path).resolve()
        payload = json.loads(source.read_text(encoding="utf-8"))
        return self.parse_dict(payload)

    def parse_dict(self, data: dict[str, Any]) -> V2Prototype1Spec:
        if not isinstance(data, dict):
            raise TypeError("V2 Prototype 1 specification must be an object.")
        body = _object(data, "body")
        manufacturing = _object(data, "manufacturing")
        output = _object(data, "output")
        text_items = data.get("texts")
        if not isinstance(text_items, list) or not all(
            isinstance(item, dict) for item in text_items
        ):
            raise TypeError("texts must be an array of objects.")

        spec = V2Prototype1Spec(
            id=str(data.get("id", "v2_prototype_1_dobo")),
            body=PrototypeBodySpec(
                template=str(body.get("template", "basic_round_01")),
                color=str(body.get("color", "white")),
                height_mm=float(body["height_mm"]),
                bottom_radius_mm=float(body["bottom_radius_mm"]),
                top_radius_mm=float(body["top_radius_mm"]),
                wall_mm=float(body["wall_mm"]),
                bottom_mm=float(body["bottom_mm"]),
            ),
            texts=tuple(
                PrototypeTextSpec(
                    content=str(item["content"]),
                    size_mm=float(item["size_mm"]),
                    depth_mm=float(item["depth_mm"]),
                    font=str(item.get("font", "Arial")),
                    kind=str(item.get("kind", "regular")),
                    width_fraction=float(item["width_fraction"]),
                    height_fraction=float(item["height_fraction"]),
                    u_center=float(item["u_center"]),
                    v_center=float(item["v_center"]),
                )
                for item in text_items
            ),
            manufacturing=PrototypeManufacturingSpec(
                process=str(manufacturing["process"]),
                colors=int(manufacturing["colors"]),
                nozzle_mm=float(manufacturing["nozzle_mm"]),
                layer_height_mm=float(manufacturing["layer_height_mm"]),
                max_generation_seconds=float(
                    manufacturing["max_generation_seconds"]
                ),
            ),
            output=PrototypeOutputSpec(
                directory=Path(str(output["directory"])),
                basename=str(output["basename"]),
                mesh_tolerance_mm=float(
                    output.get("mesh_tolerance_mm", 0.08)
                ),
                angular_tolerance=float(
                    output.get("angular_tolerance", 0.15)
                ),
            ),
        )
        spec.validate()
        return spec


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a JSON object.")
    return value
