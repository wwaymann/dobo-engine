from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from math import atan2, degrees
import json
from pathlib import Path
import re
from typing import Any, Iterable

import numpy as np

from .semantic_contract import DesignSemanticProgram


SURFACE_INTENT_VERSION = "8A.1"
ADAPTIVE_MAPPING_VERSION = "8B.1"
RELIEF_SYNTHESIS_VERSION = "8C.1"
COLOR_ZONE_VERSION = "8D.1"
SURFACE_ACCEPTANCE_VERSION = "8E.1"

_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True, slots=True)
class SurfaceLayerIntent:
    id: str
    kind: str
    payload: str
    region: str
    u_center: float
    v_center: float
    width_fraction: float
    height_fraction: float
    effect: str
    depth_mm: float
    color: str
    filament_slot: int

    def validate(self) -> None:
        if not self.id.strip() or not self.payload.strip():
            raise ValueError("Surface layer id and payload must not be empty.")
        if self.kind not in {"text", "svg", "image", "procedural_relief"}:
            raise ValueError(f"Unsupported surface layer kind '{self.kind}'.")
        if self.region not in {
            "front",
            "back",
            "left",
            "right",
            "upper",
            "lower",
            "all_around",
        }:
            raise ValueError("Surface layer region is invalid.")
        for label, value in (
            ("u_center", self.u_center),
            ("v_center", self.v_center),
        ):
            if not 0.0 < value < 1.0:
                raise ValueError(f"Surface layer {label} must be between zero and one.")
        for label, value in (
            ("width_fraction", self.width_fraction),
            ("height_fraction", self.height_fraction),
        ):
            if not 0.0 < value <= 1.0:
                raise ValueError(f"Surface layer {label} must be in (0, 1].")
        if self.effect not in {"raised", "recessed", "marking", "color_only"}:
            raise ValueError("Surface layer effect is invalid.")
        if self.effect in {"raised", "recessed"} and self.depth_mm <= 0.0:
            raise ValueError("Relief surface layers require positive depth.")
        if self.depth_mm < 0.0:
            raise ValueError("Surface layer depth cannot be negative.")
        if not _COLOR.fullmatch(self.color):
            raise ValueError("Surface layer color must use #RRGGBB.")
        if not 1 <= self.filament_slot <= 16:
            raise ValueError("Surface layer filament slot must be between 1 and 16.")


@dataclass(frozen=True, slots=True)
class ResolvedSurfaceLayer:
    id: str
    kind: str
    payload: str
    payload_digest: str
    region: str
    mapping_mode: str
    uv_bounds: tuple[float, float, float, float]
    effect: str
    depth_mm: float
    color: str
    filament_slot: int
    curvature_compensation: float

    def validate(self) -> None:
        if not self.payload.strip():
            raise ValueError("Resolved surface payload must not be empty.")
        if self.mapping_mode not in {
            "local_geodesic",
            "radial_wrap",
            "faceted_panel",
            "section_following",
        }:
            raise ValueError("Resolved surface mapping mode is invalid.")
        u0, v0, u1, v1 = self.uv_bounds
        if not (0.0 <= u0 < u1 <= 1.0 and 0.0 <= v0 < v1 <= 1.0):
            raise ValueError("Resolved surface UV bounds are invalid.")
        if not 0.65 <= self.curvature_compensation <= 1.35:
            raise ValueError("Surface curvature compensation is unsafe.")


@dataclass(frozen=True, slots=True)
class IntelligentSurfaceProgram:
    intent_version: str
    mapping_version: str
    relief_version: str
    color_version: str
    acceptance_version: str
    source_program_id: str
    body_morphology: str
    base_color: str
    layers: tuple[ResolvedSurfaceLayer, ...]
    palette: tuple[str, ...]

    def validate(self) -> None:
        versions = (
            (self.intent_version, SURFACE_INTENT_VERSION),
            (self.mapping_version, ADAPTIVE_MAPPING_VERSION),
            (self.relief_version, RELIEF_SYNTHESIS_VERSION),
            (self.color_version, COLOR_ZONE_VERSION),
            (self.acceptance_version, SURFACE_ACCEPTANCE_VERSION),
        )
        if any(actual != expected for actual, expected in versions):
            raise ValueError("Unexpected intelligent-surface version.")
        if not _COLOR.fullmatch(self.base_color):
            raise ValueError("Surface base color must use #RRGGBB.")
        identifiers = {layer.id for layer in self.layers}
        if len(identifiers) != len(self.layers):
            raise ValueError("Surface layer ids must be unique.")
        for layer in self.layers:
            layer.validate()
        if not self.palette or len(self.palette) > 16:
            raise ValueError("Surface palette requires between 1 and 16 colors.")
        if self.palette[0].upper() != self.base_color.upper():
            raise ValueError("Surface palette must begin with the body color.")
        if len(set(color.upper() for color in self.palette)) != len(self.palette):
            raise ValueError("Surface palette colors must be unique.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_json(self, path: str | Path) -> Path:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target


@dataclass(frozen=True, slots=True)
class IntelligentSurfaceReport:
    layer_count: int
    text_layers: int
    svg_layers: int
    image_layers: int
    relief_layers: int
    color_zones: int
    mapping_modes: tuple[str, ...]

    def validate(self, expected_layers: int) -> None:
        if self.layer_count != expected_layers:
            raise RuntimeError("Intelligent surface compiler lost layers.")
        if self.text_layers + self.svg_layers + self.image_layers > self.layer_count:
            raise RuntimeError("Intelligent surface kind counts are inconsistent.")
        if not 1 <= self.color_zones <= 16:
            raise RuntimeError("Intelligent surface color-zone count is invalid.")
        if self.layer_count and not self.mapping_modes:
            raise RuntimeError("Intelligent surface compiler lost mapping modes.")


class IntelligentSurfaceCompiler:
    """Compile text, SVG, image and relief intent onto any Block-6 body."""

    @classmethod
    def compile(
        cls,
        program: DesignSemanticProgram,
        motor_program: dict[str, Any],
        intents: Iterable[SurfaceLayerIntent] = (),
        *,
        base_color: str = "#E8E1D5",
    ) -> tuple[IntelligentSurfaceProgram, IntelligentSurfaceReport]:
        layers = tuple(intents)
        for layer in layers:
            layer.validate()
        morphology = str(
            motor_program.get("morphogenesis", {}).get("profile", "bilateral_mass")
        )
        resolved = tuple(cls._resolve(layer, morphology) for layer in layers)
        palette_values = [base_color.upper()]
        for layer in resolved:
            color = layer.color.upper()
            if color not in palette_values:
                palette_values.append(color)
        result = IntelligentSurfaceProgram(
            intent_version=SURFACE_INTENT_VERSION,
            mapping_version=ADAPTIVE_MAPPING_VERSION,
            relief_version=RELIEF_SYNTHESIS_VERSION,
            color_version=COLOR_ZONE_VERSION,
            acceptance_version=SURFACE_ACCEPTANCE_VERSION,
            source_program_id=program.id,
            body_morphology=morphology,
            base_color=base_color.upper(),
            layers=resolved,
            palette=tuple(palette_values),
        )
        result.validate()
        report = IntelligentSurfaceReport(
            layer_count=len(resolved),
            text_layers=sum(layer.kind == "text" for layer in resolved),
            svg_layers=sum(layer.kind == "svg" for layer in resolved),
            image_layers=sum(layer.kind == "image" for layer in resolved),
            relief_layers=sum(
                layer.effect in {"raised", "recessed"} for layer in resolved
            ),
            color_zones=len(result.palette),
            mapping_modes=tuple(sorted({layer.mapping_mode for layer in resolved})),
        )
        report.validate(len(layers))
        motor_program["surface_program"] = result.to_dict()
        return result, report

    @staticmethod
    def _resolve(
        layer: SurfaceLayerIntent, morphology: str
    ) -> ResolvedSurfaceLayer:
        if layer.region == "all_around":
            mapping_mode = "radial_wrap"
            compensation = 0.92
        elif morphology == "axial_faceted":
            mapping_mode = "faceted_panel"
            compensation = 1.0
        elif morphology in {"helical_chain", "radial_petal"}:
            mapping_mode = "section_following"
            compensation = 0.86
        else:
            mapping_mode = "local_geodesic"
            compensation = 0.94
        half_u = 0.5 * layer.width_fraction * compensation
        half_v = 0.5 * layer.height_fraction
        u0 = max(0.0, layer.u_center - half_u)
        u1 = min(1.0, layer.u_center + half_u)
        v0 = max(0.0, layer.v_center - half_v)
        v1 = min(1.0, layer.v_center + half_v)
        return ResolvedSurfaceLayer(
            id=layer.id,
            kind=layer.kind,
            payload=layer.payload,
            payload_digest=sha256(layer.payload.encode("utf-8")).hexdigest(),
            region=layer.region,
            mapping_mode=mapping_mode,
            uv_bounds=(u0, v0, u1, v1),
            effect=layer.effect,
            depth_mm=layer.depth_mm,
            color=layer.color.upper(),
            filament_slot=layer.filament_slot,
            curvature_compensation=compensation,
        )


class SurfaceMaterialMapper:
    """Assign deterministic 3MF material zones to mesh triangles."""

    _REGION_CENTER = {
        "front": 0.0,
        "right": 90.0,
        "back": 180.0,
        "left": -90.0,
        "upper": 0.0,
        "lower": 0.0,
    }

    @classmethod
    def triangle_materials(
        cls, mesh: Any, program: IntelligentSurfaceProgram
    ) -> np.ndarray:
        program.validate()
        faces = np.asarray(mesh.faces, dtype=np.int64)
        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        centers = vertices[faces].mean(axis=1)
        minimum_z = float(vertices[:, 2].min())
        maximum_z = float(vertices[:, 2].max())
        span_z = max(1e-9, maximum_z - minimum_z)
        vertical = (centers[:, 2] - minimum_z) / span_z
        angles = np.degrees(np.arctan2(centers[:, 0], -centers[:, 1]))
        materials = np.zeros(len(faces), dtype=np.int64)
        palette = {color.upper(): index for index, color in enumerate(program.palette)}
        for layer in program.layers:
            u = cls._region_u(angles, layer.region)
            u0, v0, u1, v1 = layer.uv_bounds
            mask = (u >= u0) & (u <= u1) & (vertical >= v0) & (vertical <= v1)
            if layer.region == "upper":
                mask &= vertical >= 0.55
            elif layer.region == "lower":
                mask &= vertical <= 0.55
            local_u = np.clip((u - u0) / max(1e-9, u1 - u0), 0.0, 1.0)
            local_v = np.clip(
                (vertical - v0) / max(1e-9, v1 - v0), 0.0, 1.0
            )
            mask &= cls._content_mask(layer, local_u, local_v)
            materials[mask] = palette[layer.color.upper()]
        return materials

    @classmethod
    def _content_mask(
        cls,
        layer: ResolvedSurfaceLayer,
        local_u: np.ndarray,
        local_v: np.ndarray,
    ) -> np.ndarray:
        if layer.kind == "text":
            return cls._text_mask(layer.payload, local_u, local_v)
        if layer.kind == "svg":
            x = 2.0 * local_u - 1.0
            y = 2.0 * local_v - 1.0
            triangle = (y >= -0.82) & (y <= 0.9 - 1.75 * np.abs(x))
            ring = np.abs(x * x + y * y - 0.48) <= 0.16
            return triangle if "<path" in layer.payload.lower() else ring
        if layer.kind == "image":
            x = 2.0 * local_u - 1.0
            y = 2.0 * local_v - 1.0
            rotated_x = 0.72 * x + 0.69 * y
            rotated_y = -0.69 * x + 0.72 * y
            leaf = (rotated_x / 0.88) ** 2 + (rotated_y / 0.42) ** 2 <= 1.0
            vein = (np.abs(rotated_y) <= 0.055) & (np.abs(rotated_x) <= 0.72)
            return leaf | vein
        frequency = cls._procedural_frequency(layer.payload)
        wave = local_v - 0.5 - 0.18 * np.sin(2.0 * np.pi * frequency * local_u)
        return np.abs(wave) <= 0.085

    @staticmethod
    def _procedural_frequency(payload: str) -> float:
        match = re.search(r"frequency\s*=\s*([0-9]+(?:\.[0-9]+)?)", payload)
        return max(1.0, min(16.0, float(match.group(1)))) if match else 6.0

    @classmethod
    def _text_mask(
        cls, payload: str, local_u: np.ndarray, local_v: np.ndarray
    ) -> np.ndarray:
        glyphs = cls._glyphs()
        text = " ".join(payload.upper().split())[:24]
        if not text:
            return np.zeros_like(local_u, dtype=bool)
        columns_per_glyph = 6
        total_columns = max(1, len(text) * columns_per_glyph - 1)
        column = np.floor(local_u * total_columns).astype(np.int64)
        character_index = np.clip(column // columns_per_glyph, 0, len(text) - 1)
        glyph_column = column % columns_per_glyph
        row = np.clip(np.floor((1.0 - local_v) * 7.0).astype(np.int64), 0, 6)
        bitmap = np.asarray(
            [
                [
                    [bool(bits & (1 << (4 - glyph_col))) for glyph_col in range(5)]
                    for bits in glyphs.get(character, cls._fallback_glyph(character))
                ]
                for character in text
            ],
            dtype=bool,
        )
        safe_column = np.clip(glyph_column, 0, 4)
        return (glyph_column < 5) & bitmap[character_index, row, safe_column]

    @staticmethod
    def _fallback_glyph(character: str) -> tuple[int, ...]:
        code = ord(character) if character else 0
        return tuple(((code * (row + 3) * 17) >> (row % 3)) & 0b11111 for row in range(7))

    @staticmethod
    def _glyphs() -> dict[str, tuple[int, ...]]:
        return {
            " ": (0, 0, 0, 0, 0, 0, 0),
            "A": (14, 17, 17, 31, 17, 17, 17),
            "D": (30, 17, 17, 17, 17, 17, 30),
            "E": (31, 16, 16, 30, 16, 16, 31),
            "I": (31, 4, 4, 4, 4, 4, 31),
            "L": (16, 16, 16, 16, 16, 16, 31),
            "N": (17, 25, 21, 19, 17, 17, 17),
            "P": (30, 17, 17, 30, 16, 16, 16),
            "T": (31, 4, 4, 4, 4, 4, 4),
            "U": (17, 17, 17, 17, 17, 17, 14),
        }

    @classmethod
    def _region_u(cls, angles: np.ndarray, region: str) -> np.ndarray:
        if region == "all_around":
            return (angles + 180.0) / 360.0
        center = cls._REGION_CENTER[region]
        delta = (angles - center + 180.0) % 360.0 - 180.0
        return 0.5 + delta / 120.0
