from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TextCompositionSpec:
    content: str
    mode: str
    depth: float
    size: float
    font: str = "Arial"
    kind: str = "bold"
    width_fraction: float = 0.32
    height_fraction: float = 0.18
    u_center: float = 0.50
    v_center: float = 0.64

    def validate(self) -> None:
        if not self.content.strip():
            raise ValueError("text.content must not be empty.")
        if self.mode not in {"emboss", "deboss"}:
            raise ValueError("text.mode must be 'emboss' or 'deboss'.")
        if self.depth <= 0.0:
            raise ValueError("text.depth must be positive.")
        if self.size <= 0.0:
            raise ValueError("text.size must be positive.")


@dataclass(frozen=True, slots=True)
class SvgCompositionSpec:
    svg: str
    mode: str
    depth: float
    width_fraction: float = 0.25
    height_fraction: float = 0.17
    u_center: float = 0.50
    v_center: float = 0.38
    document_id: str = "json_product_svg"

    def validate(self) -> None:
        if "<svg" not in self.svg.lower():
            raise ValueError("svg.svg must contain SVG markup.")
        if self.mode not in {"emboss", "deboss"}:
            raise ValueError("svg.mode must be 'emboss' or 'deboss'.")
        if self.depth <= 0.0:
            raise ValueError("svg.depth must be positive.")


@dataclass(frozen=True, slots=True)
class ProductCompositionSpec:
    id: str
    body: str
    primitives: bool
    booleans: bool
    geometric_decoration: bool
    text: TextCompositionSpec | None
    svg: SvgCompositionSpec | None
    output_filename: str

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("id must not be empty.")
        if self.body != "phase4_organic":
            raise ValueError("Phase 5 currently supports body='phase4_organic' only.")
        if self.text is not None:
            self.text.validate()
        if self.svg is not None:
            self.svg.validate()
        if not self.output_filename.lower().endswith(".step"):
            raise ValueError("output_filename must end with .step.")


class ProductCompositionParser:
    def parse_dict(self, data: dict[str, Any]) -> ProductCompositionSpec:
        if not isinstance(data, dict):
            raise TypeError("Product composition must be a JSON object.")
        text_data = data.get("text")
        svg_data = data.get("svg")
        text_spec = None if text_data is None else TextCompositionSpec(
            content=str(text_data["content"]),
            mode=str(text_data.get("mode", "emboss")).lower(),
            depth=float(text_data.get("depth", 1.8)),
            size=float(text_data.get("size", 12.0)),
            font=str(text_data.get("font", "Arial")),
            kind=str(text_data.get("kind", "bold")),
            width_fraction=float(text_data.get("width_fraction", 0.32)),
            height_fraction=float(text_data.get("height_fraction", 0.18)),
            u_center=float(text_data.get("u_center", 0.50)),
            v_center=float(text_data.get("v_center", 0.64)),
        )
        svg_spec = None if svg_data is None else SvgCompositionSpec(
            svg=str(svg_data["svg"]),
            mode=str(svg_data.get("mode", "deboss")).lower(),
            depth=float(svg_data.get("depth", 1.4)),
            width_fraction=float(svg_data.get("width_fraction", 0.25)),
            height_fraction=float(svg_data.get("height_fraction", 0.17)),
            u_center=float(svg_data.get("u_center", 0.50)),
            v_center=float(svg_data.get("v_center", 0.38)),
            document_id=str(svg_data.get("document_id", "json_product_svg")),
        )
        spec = ProductCompositionSpec(
            id=str(data.get("id", "dobo_json_product")),
            body=str(data.get("body", "phase4_organic")),
            primitives=bool(data.get("primitives", True)),
            booleans=bool(data.get("booleans", True)),
            geometric_decoration=bool(data.get("geometric_decoration", True)),
            text=text_spec,
            svg=svg_spec,
            output_filename=str(data.get("output_filename", "dobo_json_product.step")),
        )
        spec.validate()
        return spec

    def parse_string(self, payload: str) -> ProductCompositionSpec:
        return self.parse_dict(json.loads(payload))

    def parse_file(self, path: str | Path) -> ProductCompositionSpec:
        return self.parse_string(Path(path).read_text(encoding="utf-8"))
