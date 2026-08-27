from __future__ import annotations

"""Runtime repair bridge for the DOBO capability laboratory.

This module deliberately limits itself to defects exposed by the live lab:
- neutral primitive envelopes (no unsolicited axial bands),
- safe vessel voxel resolution,
- physical stroke text for semantic text features,
- curvature-aware wrapping so raised text follows curved vessels.

The bridge is installed only by ``dobo_capability_lab_live.py`` so every repaired
behaviour remains directly observable before it is promoted deeper into the core.
"""

from copy import deepcopy
from typing import Any
import unicodedata

import numpy as np

from product_generators.design_interpreter.body_family_expansion import GeneralBodyFamilyExpander
from product_generators.design_interpreter.semantic_compiler import SemanticToMotorCompiler
from product_generators.design_interpreter.structural_pipeline import DoboStructuralPipeline
from product_generators.organic_shapes.feature_program_engine import FeatureProgramVesselEngine
from product_generators.organic_shapes.vessel_specification import OrganicVesselParser


_TEXT_TEMPLATES: dict[str, str] = {}
_TEXT_WRAP_RADIUS: dict[str, float] = {}
_TEXT_GENERATION_BUDGET_SECONDS = 120.0
_ORIGINAL_FIELD = FeatureProgramVesselEngine._feature_field
_ORIGINAL_FIELDS_FOR = GeneralBodyFamilyExpander._fields_for
_ORIGINAL_REQUESTED_PROFILE = GeneralBodyFamilyExpander.requested_profile
_ORIGINAL_PARSE = OrganicVesselParser.parse_dict
_ORIGINAL_COMPILE_FEATURE = SemanticToMotorCompiler._compile_feature.__func__


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _literal_from_concept(concept: str) -> str:
    tokens = [token for token in _plain(concept).split("_") if token]
    generic = {"text", "texto", "label", "name", "nombre", "word", "palabra"}
    literal = [token for token in tokens if token not in generic]
    return " ".join(literal or tokens).upper()[:18]


def _paired(field: dict[str, Any], second_id: str) -> list[dict[str, Any]]:
    other = deepcopy(field)
    other["id"] = second_id
    return [field, other]


def _neutral_fields_for(cls, profile: str, program):
    width = float(program.body.width_mm)
    depth = float(program.body.depth_mm)
    height = float(program.body.height_mm)
    minimum = min(width, depth, height)
    round_mm = max(0.8, minimum * 0.012)

    if profile == "cylindrical":
        field = cls._faceted(
            "body", [0.0, 0.0, 0.0],
            [0.49 * width, 0.49 * depth, 0.47 * height],
            sides=64, exponent=8.0, round_mm=round_mm,
        )
        return _paired(field, "cylindrical_support"), max(1.0, minimum * 0.012)

    if profile in {"cuboid", "rectangular_prism"}:
        field = cls._superellipsoid(
            "body", [0.0, 0.0, 0.0],
            [0.49 * width, 0.49 * depth, 0.47 * height],
            exponent=8.0, round_mm=max(1.0, minimum * 0.014),
        )
        return _paired(field, f"{profile}_support"), max(1.0, minimum * 0.012)

    if profile == "triangular_prism":
        field = cls._faceted(
            "body", [0.0, 0.0, 0.0],
            [0.49 * width, 0.49 * depth, 0.47 * height],
            sides=3, exponent=8.0, round_mm=round_mm, rotation_degrees=30.0,
        )
        return _paired(field, "triangular_support"), max(0.9, minimum * 0.010)

    if profile in {"ovoid", "spherical"}:
        exponent = 2.0 if profile == "spherical" else 2.15
        radii = (
            [0.49 * width, 0.49 * depth, 0.47 * height]
            if profile == "spherical"
            else [0.46 * width, 0.44 * depth, 0.49 * height]
        )
        field = cls._superellipsoid(
            "body", [0.0, 0.0, 0.0], radii,
            exponent=exponent, round_mm=max(1.0, minimum * 0.014),
        )
        return _paired(field, f"{profile}_support"), max(1.0, minimum * 0.012)

    if profile == "tapered_revolution":
        fields: list[dict[str, Any]] = []
        sections = (
            (-0.36, 0.34), (-0.24, 0.36), (-0.12, 0.38),
            (0.00, 0.405), (0.12, 0.43), (0.24, 0.455), (0.36, 0.48),
        )
        for index, (z_ratio, radius_ratio) in enumerate(sections):
            fields.append(
                cls._superellipsoid(
                    "body" if index == 0 else f"tapered_section_{index}",
                    [0.0, 0.0, z_ratio * height],
                    [radius_ratio * width, radius_ratio * depth, 0.17 * height],
                    exponent=3.0, round_mm=round_mm,
                )
            )
        return fields, max(2.2, minimum * 0.025)

    return _ORIGINAL_FIELDS_FOR(profile, program)


def _requested_profile(cls, program):
    family = _plain(program.body.family).replace("-", "_").replace(" ", "_")
    tags = {_plain(tag).replace("-", "_").replace(" ", "_") for tag in program.body.style_tags}
    if family == "spherical" or "spherical" in tags or "sphere" in tags:
        return "spherical"
    return _ORIGINAL_REQUESTED_PROFILE(program)


def _safe_parse(self, data: dict[str, Any]):
    repaired = deepcopy(data)
    grid = repaired.get("grid")
    vessel = repaired.get("vessel")
    if isinstance(grid, dict) and isinstance(vessel, dict):
        voxel = float(grid.get("voxel_mm", 1.0))
        wall = float(vessel.get("wall_mm", 0.0))
        bottom = float(vessel.get("cavity_floor_z_mm", 0.0)) - float(vessel.get("base_z_mm", 0.0))
        spans = [value for value in (wall, bottom) if value > 0.0]
        if spans:
            grid["voxel_mm"] = min(voxel, min(spans) / 3.05)
    return _ORIGINAL_PARSE(self, repaired)


def _compile_feature_with_text(cls, feature, **kwargs):
    template, transform = _ORIGINAL_COMPILE_FEATURE(cls, feature, **kwargs)
    if feature.form_hint == "text":
        template["semantic_kind"] = "text_stroke"
        template["text_literal"] = _literal_from_concept(feature.concept)
    return template, transform


_SEG = {
    "a": ((-0.38, 0.50), (0.38, 0.50)), "b": ((0.38, 0.50), (0.38, 0.00)),
    "c": ((0.38, 0.00), (0.38, -0.50)), "d": ((-0.38, -0.50), (0.38, -0.50)),
    "e": ((-0.38, 0.00), (-0.38, -0.50)), "f": ((-0.38, 0.50), (-0.38, 0.00)),
    "g": ((-0.38, 0.00), (0.38, 0.00)), "h": ((-0.38, 0.50), (0.00, 0.00)),
    "i": ((0.38, 0.50), (0.00, 0.00)), "j": ((-0.38, -0.50), (0.00, 0.00)),
    "k": ((0.38, -0.50), (0.00, 0.00)), "l": ((0.00, 0.50), (0.00, 0.00)),
    "m": ((0.00, 0.00), (0.00, -0.50)),
}
_GLYPH = {
    "A": "abcefg", "B": "abcdefg", "C": "adef", "D": "abcdef", "E": "adefg",
    "F": "aefg", "G": "acdefg", "H": "bcefg", "I": "adlm", "J": "bcde",
    "K": "efhik", "L": "def", "M": "bcefhi", "N": "bcefhk", "O": "abcdef",
    "P": "abefg", "Q": "abcdefk", "R": "abefgk", "S": "acdfg", "T": "alm",
    "U": "bcdef", "V": "efjk", "W": "bcefjk", "X": "hijk", "Y": "hilm",
    "Z": "adij", "0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg",
    "4": "bcfg", "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg",
    "9": "abcdfg", "-": "g",
}


def _segment_prism(x, y, z, x1, z1, x2, z2, radius, half_depth):
    dx = x2 - x1
    dz = z2 - z1
    denom = dx * dx + dz * dz
    t = np.clip(((x - x1) * dx + (z - z1) * dz) / max(denom, 1e-12), 0.0, 1.0)
    px = x1 + t * dx
    pz = z1 + t * dz
    radial = np.sqrt((x - px) ** 2 + (z - pz) ** 2) - radius
    slab = np.abs(y) - half_depth
    outside = np.sqrt(np.maximum(radial, 0.0) ** 2 + np.maximum(slab, 0.0) ** 2)
    inside = np.minimum(np.maximum(radial, slab), 0.0)
    return outside + inside


def _cylindrical_text_coordinates(local_x, local_y, wrap_radius: float | None):
    if wrap_radius is None or wrap_radius <= 0.0:
        return local_x, local_y
    radius = float(wrap_radius)
    centre_y = radius - local_y
    angle = np.arctan2(local_x, centre_y)
    arc_x = radius * angle
    radial_distance = np.sqrt(local_x * local_x + centre_y * centre_y)
    depth = radius - radial_distance
    return arc_x, depth


def _text_field(feature, text: str, x, y, z, *, wrap_radius: float | None = None):
    half_sizes = feature.half_sizes
    if half_sizes is None:
        return _ORIGINAL_FIELD(feature, x, y, z)
    center = feature.center or (0.0, 0.0, 0.0)
    local_x = x - float(center[0])
    local_y = y - float(center[1])
    local_z = z - float(center[2])
    local_x, local_y = _cylindrical_text_coordinates(local_x, local_y, wrap_radius)
    total_width = 2.0 * float(half_sizes[0])
    total_height = 2.0 * float(half_sizes[2])
    half_depth = float(half_sizes[1])
    visible = text or "TEXT"
    count = max(1, len(visible))
    cell_width = total_width / count
    stroke = max(0.32, min(0.10 * cell_width, 0.075 * total_height))
    result = None
    for index, character in enumerate(visible):
        if character == " ":
            continue
        center_x = -0.5 * total_width + (index + 0.5) * cell_width
        segments = _GLYPH.get(character, "hijk")
        for name in segments:
            (sx1, sz1), (sx2, sz2) = _SEG[name]
            distance = _segment_prism(
                local_x, local_y, local_z,
                center_x + sx1 * cell_width, sz1 * total_height,
                center_x + sx2 * cell_width, sz2 * total_height,
                stroke, half_depth,
            )
            result = distance if result is None else np.minimum(result, distance)
    return result if result is not None else _ORIGINAL_FIELD(feature, x, y, z)


def _feature_field(feature, x, y, z):
    text = _TEXT_TEMPLATES.get(feature.id)
    if text:
        return _text_field(feature, text, x, y, z, wrap_radius=_TEXT_WRAP_RADIUS.get(feature.id))
    return _ORIGINAL_FIELD(feature, x, y, z)


class RepairedStructuralPipeline(DoboStructuralPipeline):
    def generate_from_semantic(self, program, **kwargs):
        _TEXT_TEMPLATES.clear()
        _TEXT_WRAP_RADIUS.clear()
        profile = GeneralBodyFamilyExpander.requested_profile(program)
        has_text = False
        for feature in program.features:
            if feature.form_hint != "text":
                continue
            has_text = True
            template_id = f"{feature.id}_template"
            _TEXT_TEMPLATES[template_id] = _literal_from_concept(feature.concept)
            if profile in {"cylindrical", "tapered_revolution"}:
                _TEXT_WRAP_RADIUS[template_id] = 0.49 * float(program.body.width_mm)
        result = super().generate_from_semantic(program, **kwargs)
        if has_text:
            object.__setattr__(result.mesh_result, "max_generation_seconds", _TEXT_GENERATION_BUDGET_SECONDS)
        return result


def install() -> type[DoboStructuralPipeline]:
    GeneralBodyFamilyExpander._fields_for = classmethod(_neutral_fields_for)
    GeneralBodyFamilyExpander.requested_profile = classmethod(_requested_profile)
    OrganicVesselParser.parse_dict = _safe_parse
    SemanticToMotorCompiler._compile_feature = classmethod(_compile_feature_with_text)
    FeatureProgramVesselEngine._feature_field = staticmethod(_feature_field)
    return RepairedStructuralPipeline
