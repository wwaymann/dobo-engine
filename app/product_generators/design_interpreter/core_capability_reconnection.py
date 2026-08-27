from __future__ import annotations

"""Promote proven Capability Lab repairs into the canonical DOBO core path.

This module does not create a second pipeline.  It installs the behaviours that
were already exercised by ``tools/dobo_capability_repairs.py`` onto the reusable
classes consumed by ``DoboStructuralPipeline``:

- neutral primitive envelopes,
- safe vessel voxel resolution,
- physical stroke text instead of a rounded-box plate,
- curvature-aware text wrapping for cylindrical/tapered vessels,
- a generation budget appropriate for physical text extraction.

The goal is transitional consolidation: the standard pipeline gets the proven
behaviour directly, while the laboratory patch remains only as historical
regression evidence.
"""

from copy import deepcopy
from typing import Any
import unicodedata

import numpy as np

from .body_family_expansion import GeneralBodyFamilyExpander
from .design_pipeline import DoboDesignPipeline
from .semantic_compiler import SemanticToMotorCompiler
from product_generators.organic_shapes.feature_program_engine import (
    FeatureProgramVesselEngine,
)
from product_generators.organic_shapes.vessel_specification import (
    OrganicVesselParser,
)


CORE_CAPABILITY_RECONNECTION_VERSION = "C0R.1"
_TEXT_GENERATION_BUDGET_SECONDS = 120.0
_TEXT_TEMPLATES: dict[str, str] = {}
_TEXT_WRAP_RADIUS: dict[str, float] = {}
_TEXT_MIN_STROKE: dict[str, float] = {}
_INSTALLED = False

_ORIGINAL_FIELD = FeatureProgramVesselEngine._feature_field
_ORIGINAL_FIELDS_FOR = GeneralBodyFamilyExpander._fields_for
_ORIGINAL_REQUESTED_PROFILE = GeneralBodyFamilyExpander.requested_profile
_ORIGINAL_APPLY = GeneralBodyFamilyExpander.apply.__func__
_ORIGINAL_PARSE = OrganicVesselParser.parse_dict
_ORIGINAL_COMPILE_FEATURE = SemanticToMotorCompiler._compile_feature.__func__
_ORIGINAL_GENERATE_WITH_RETRY = DoboDesignPipeline._generate_with_retry.__func__


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )


def _literal_from_concept(concept: str) -> str:
    tokens = [token for token in _plain(concept).split("_") if token]
    generic = {
        "text",
        "texto",
        "label",
        "name",
        "nombre",
        "word",
        "palabra",
    }
    literal = [token for token in tokens if token not in generic]
    return " ".join(literal or tokens).upper()[:24]


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
        # Keep the native cylindrical field from the canonical family expander.
        return _ORIGINAL_FIELDS_FOR(profile, program)

    if profile in {"cuboid", "rectangular_prism"}:
        field = cls._superellipsoid(
            "body",
            [0.0, 0.0, 0.0],
            [0.49 * width, 0.49 * depth, 0.47 * height],
            exponent=8.0,
            round_mm=max(1.0, minimum * 0.014),
        )
        return _paired(field, f"{profile}_support"), max(
            1.0, minimum * 0.012
        )

    if profile == "triangular_prism":
        field = cls._faceted(
            "body",
            [0.0, 0.0, 0.0],
            [0.49 * width, 0.49 * depth, 0.47 * height],
            sides=3,
            exponent=8.0,
            round_mm=round_mm,
            rotation_degrees=30.0,
        )
        return _paired(field, "triangular_support"), max(
            0.9, minimum * 0.010
        )

    if profile in {"ovoid", "spherical"}:
        exponent = 2.0 if profile == "spherical" else 2.15
        radii = (
            [0.49 * width, 0.49 * depth, 0.47 * height]
            if profile == "spherical"
            else [0.46 * width, 0.44 * depth, 0.49 * height]
        )
        field = cls._superellipsoid(
            "body",
            [0.0, 0.0, 0.0],
            radii,
            exponent=exponent,
            round_mm=max(1.0, minimum * 0.014),
        )
        return _paired(field, f"{profile}_support"), max(
            1.0, minimum * 0.012
        )

    if profile == "tapered_revolution":
        fields: list[dict[str, Any]] = []
        sections = (
            (-0.36, 0.34),
            (-0.24, 0.36),
            (-0.12, 0.38),
            (0.00, 0.405),
            (0.12, 0.43),
            (0.24, 0.455),
            (0.36, 0.48),
        )
        for index, (z_ratio, radius_ratio) in enumerate(sections):
            fields.append(
                cls._superellipsoid(
                    "body" if index == 0 else f"tapered_section_{index}",
                    [0.0, 0.0, z_ratio * height],
                    [
                        radius_ratio * width,
                        radius_ratio * depth,
                        0.17 * height,
                    ],
                    exponent=3.0,
                    round_mm=round_mm,
                )
            )
        return fields, max(2.2, minimum * 0.025)

    return _ORIGINAL_FIELDS_FOR(profile, program)


def _requested_profile(cls, program):
    family = _plain(program.body.family).replace("-", "_").replace(" ", "_")
    tags = {
        _plain(tag).replace("-", "_").replace(" ", "_")
        for tag in program.body.style_tags
    }
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
        bottom = float(vessel.get("cavity_floor_z_mm", 0.0)) - float(
            vessel.get("base_z_mm", 0.0)
        )
        spans = [value for value in (wall, bottom) if value > 0.0]
        if spans:
            grid["voxel_mm"] = min(voxel, min(spans) / 3.05)
    return _ORIGINAL_PARSE(self, repaired)


def _compile_feature_with_text(cls, feature, **kwargs):
    template, transform = _ORIGINAL_COMPILE_FEATURE(cls, feature, **kwargs)
    if feature.form_hint != "text":
        return template, transform

    literal = _literal_from_concept(feature.concept)
    template["semantic_kind"] = "text_stroke"
    template["text_literal"] = literal

    # The old generic fallback represented text as a rounded box.  Keep that
    # template envelope only as the placement/bounding contract; the field
    # evaluator below replaces the box with physical glyph strokes.
    if template.get("kind") == "rounded_box" and template.get("half_sizes"):
        half_sizes = [float(value) for value in template["half_sizes"]]
        minimum_feature = float(kwargs.get("minimum_feature_mm", 0.0))
        minimum_relief = float(kwargs.get("minimum_relief_depth_mm", 0.0))
        maximum_relief = float(kwargs.get("maximum_relief_depth_mm", half_sizes[1]))
        safe_half_depth = max(
            half_sizes[1],
            0.65 * minimum_feature,
            1.01 * minimum_relief,
        )
        half_sizes[1] = min(safe_half_depth, maximum_relief)
        template["half_sizes"] = half_sizes

    return template, transform


def _apply_with_text_contract(cls, motor_program, program):
    _TEXT_TEMPLATES.clear()
    _TEXT_WRAP_RADIUS.clear()
    _TEXT_MIN_STROKE.clear()

    result = _ORIGINAL_APPLY(cls, motor_program, program)
    profile = cls.requested_profile(program)
    wrap_radius = (
        0.49 * min(float(program.body.width_mm), float(program.body.depth_mm))
        if profile in {"cylindrical", "tapered_revolution"}
        else None
    )
    templates = {
        str(item.get("id")): item
        for item in motor_program.get("hierarchy_program", {}).get("templates", [])
        if isinstance(item, dict)
    }

    for feature in program.features:
        if feature.form_hint != "text":
            continue
        template_id = f"{feature.id}_template"
        literal = _literal_from_concept(feature.concept)
        _TEXT_TEMPLATES[template_id] = literal
        _TEXT_MIN_STROKE[template_id] = max(
            0.32,
            0.52 * float(program.manufacturing.minimum_feature_mm),
        )
        if wrap_radius is not None:
            _TEXT_WRAP_RADIUS[template_id] = wrap_radius
        template = templates.get(template_id)
        if template is not None:
            template["semantic_kind"] = "text_stroke"
            template["text_literal"] = literal
            template["text_wrap_radius_mm"] = wrap_radius
            template["text_minimum_stroke_radius_mm"] = _TEXT_MIN_STROKE[
                template_id
            ]

    return result


_SEG = {
    "a": ((-0.38, 0.50), (0.38, 0.50)),
    "b": ((0.38, 0.50), (0.38, 0.00)),
    "c": ((0.38, 0.00), (0.38, -0.50)),
    "d": ((-0.38, -0.50), (0.38, -0.50)),
    "e": ((-0.38, 0.00), (-0.38, -0.50)),
    "f": ((-0.38, 0.50), (-0.38, 0.00)),
    "g": ((-0.38, 0.00), (0.38, 0.00)),
    "h": ((-0.38, 0.50), (0.00, 0.00)),
    "i": ((0.38, 0.50), (0.00, 0.00)),
    "j": ((-0.38, -0.50), (0.00, 0.00)),
    "k": ((0.38, -0.50), (0.00, 0.00)),
    "l": ((0.00, 0.50), (0.00, 0.00)),
    "m": ((0.00, 0.00), (0.00, -0.50)),
}

_GLYPH = {
    "A": "abcefg",
    "B": "abcdefg",
    "C": "adef",
    "D": "abcdef",
    "E": "adefg",
    "F": "aefg",
    "G": "acdefg",
    "H": "bcefg",
    "I": "adlm",
    "J": "bcde",
    "K": "efhik",
    "L": "def",
    "M": "bcefhi",
    "N": "bcefhk",
    "O": "abcdef",
    "P": "abefg",
    "Q": "abcdefk",
    "R": "abefgk",
    "S": "acdfg",
    "T": "alm",
    "U": "bcdef",
    "V": "efjk",
    "W": "bcefjk",
    "X": "hijk",
    "Y": "hilm",
    "Z": "adij",
    "0": "abcdef",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    "-": "g",
}


def _segment_prism(x, y, z, x1, z1, x2, z2, radius, half_depth):
    dx = x2 - x1
    dz = z2 - z1
    denominator = dx * dx + dz * dz
    t = np.clip(
        ((x - x1) * dx + (z - z1) * dz) / max(denominator, 1e-12),
        0.0,
        1.0,
    )
    px = x1 + t * dx
    pz = z1 + t * dz
    radial = np.sqrt((x - px) ** 2 + (z - pz) ** 2) - radius
    slab = np.abs(y) - half_depth
    outside = np.sqrt(
        np.maximum(radial, 0.0) ** 2 + np.maximum(slab, 0.0) ** 2
    )
    inside = np.minimum(np.maximum(radial, slab), 0.0)
    return outside + inside


def _cylindrical_text_coordinates(local_x, local_y, wrap_radius):
    if wrap_radius is None or wrap_radius <= 0.0:
        return local_x, local_y
    radius = float(wrap_radius)
    centre_y = radius - local_y
    angle = np.arctan2(local_x, centre_y)
    arc_x = radius * angle
    radial_distance = np.sqrt(local_x * local_x + centre_y * centre_y)
    depth = radius - radial_distance
    return arc_x, depth


def _text_field(
    feature,
    text: str,
    x,
    y,
    z,
    *,
    wrap_radius: float | None = None,
    minimum_stroke_radius: float = 0.32,
):
    half_sizes = feature.half_sizes
    if half_sizes is None:
        return _ORIGINAL_FIELD(feature, x, y, z)
    center = feature.center or (0.0, 0.0, 0.0)
    local_x = x - float(center[0])
    local_y = y - float(center[1])
    local_z = z - float(center[2])
    local_x, local_y = _cylindrical_text_coordinates(
        local_x, local_y, wrap_radius
    )
    total_width = 2.0 * float(half_sizes[0])
    total_height = 2.0 * float(half_sizes[2])
    half_depth = float(half_sizes[1])
    visible = text or "TEXT"
    count = max(1, len(visible))
    cell_width = total_width / count
    stroke = max(
        float(minimum_stroke_radius),
        min(0.10 * cell_width, 0.075 * total_height),
    )
    result = None
    for index, character in enumerate(visible):
        if character == " ":
            continue
        center_x = -0.5 * total_width + (index + 0.5) * cell_width
        segments = _GLYPH.get(character, "hijk")
        for name in segments:
            (sx1, sz1), (sx2, sz2) = _SEG[name]
            distance = _segment_prism(
                local_x,
                local_y,
                local_z,
                center_x + sx1 * cell_width,
                sz1 * total_height,
                center_x + sx2 * cell_width,
                sz2 * total_height,
                stroke,
                half_depth,
            )
            result = distance if result is None else np.minimum(result, distance)
    return (
        result
        if result is not None
        else _ORIGINAL_FIELD(feature, x, y, z)
    )


def _feature_field(feature, x, y, z):
    text = _TEXT_TEMPLATES.get(feature.id)
    if text:
        return _text_field(
            feature,
            text,
            x,
            y,
            z,
            wrap_radius=_TEXT_WRAP_RADIUS.get(feature.id),
            minimum_stroke_radius=_TEXT_MIN_STROKE.get(feature.id, 0.32),
        )
    return _ORIGINAL_FIELD(feature, x, y, z)


def _generate_with_text_budget(cls, motor_program, *, parser, engine):
    candidate = motor_program
    if _TEXT_TEMPLATES:
        candidate = deepcopy(motor_program)
        output = candidate.setdefault("output", {})
        output["max_generation_seconds"] = max(
            float(output.get("max_generation_seconds", 0.0)),
            _TEXT_GENERATION_BUDGET_SECONDS,
        )
    return _ORIGINAL_GENERATE_WITH_RETRY(
        cls,
        candidate,
        parser=parser,
        engine=engine,
    )


def install_core_capability_reconnection() -> str:
    """Install the proven reconnection once for the canonical engine process."""
    global _INSTALLED
    if _INSTALLED:
        return CORE_CAPABILITY_RECONNECTION_VERSION

    GeneralBodyFamilyExpander._fields_for = classmethod(_neutral_fields_for)
    GeneralBodyFamilyExpander.requested_profile = classmethod(_requested_profile)
    GeneralBodyFamilyExpander.apply = classmethod(_apply_with_text_contract)
    OrganicVesselParser.parse_dict = _safe_parse
    SemanticToMotorCompiler._compile_feature = classmethod(
        _compile_feature_with_text
    )
    FeatureProgramVesselEngine._feature_field = staticmethod(_feature_field)
    DoboDesignPipeline._generate_with_retry = classmethod(
        _generate_with_text_budget
    )
    _INSTALLED = True
    return CORE_CAPABILITY_RECONNECTION_VERSION
