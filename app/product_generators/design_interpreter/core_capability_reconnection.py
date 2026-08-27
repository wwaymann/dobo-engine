from __future__ import annotations

"""Promote the proven curved-text repair into the canonical DOBO path.

This module intentionally touches only the capability being consolidated:
semantic text -> physical glyph strokes -> curvature-aware placement -> one
printable body.  Body-family geometry, vessel parsing and morphology remain on
the pre-existing canonical implementations so a text consolidation cannot
silently redefine unrelated capabilities.
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


CORE_CAPABILITY_RECONNECTION_VERSION = "C0R.2-text-only"
_TEXT_GENERATION_BUDGET_SECONDS = 120.0
_TEXT_TEMPLATES: dict[str, str] = {}
_TEXT_WRAP_RADIUS: dict[str, float] = {}
_TEXT_MIN_STROKE: dict[str, float] = {}
_INSTALLED = False

_ORIGINAL_FIELD = FeatureProgramVesselEngine._feature_field
_ORIGINAL_APPLY = GeneralBodyFamilyExpander.apply.__func__
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


def _compile_feature_with_text(cls, feature, **kwargs):
    template, transform = _ORIGINAL_COMPILE_FEATURE(cls, feature, **kwargs)
    if feature.form_hint != "text":
        return template, transform

    literal = _literal_from_concept(feature.concept)
    template["semantic_kind"] = "text_stroke"
    template["text_literal"] = literal

    # The generic compiler still provides the placement envelope.  Geometry is
    # replaced below by physical strokes, so the rounded box never reaches the
    # final mesh as a plaque.
    if template.get("kind") == "rounded_box" and template.get("half_sizes"):
        half_sizes = [float(value) for value in template["half_sizes"]]
        minimum_feature = float(kwargs.get("minimum_feature_mm", 0.0))
        minimum_relief = float(kwargs.get("minimum_relief_depth_mm", 0.0))
        maximum_relief = float(
            kwargs.get("maximum_relief_depth_mm", half_sizes[1])
        )
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

    # Preserve the canonical body-family expansion exactly as it was before
    # this reconnection.
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
        local_x,
        local_y,
        wrap_radius,
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
    return result if result is not None else _ORIGINAL_FIELD(feature, x, y, z)


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
    """Install the text reconnection once for the canonical engine process."""
    global _INSTALLED
    if _INSTALLED:
        return CORE_CAPABILITY_RECONNECTION_VERSION

    GeneralBodyFamilyExpander.apply = classmethod(_apply_with_text_contract)
    SemanticToMotorCompiler._compile_feature = classmethod(
        _compile_feature_with_text
    )
    FeatureProgramVesselEngine._feature_field = staticmethod(_feature_field)
    DoboDesignPipeline._generate_with_retry = classmethod(
        _generate_with_text_budget
    )
    _INSTALLED = True
    return CORE_CAPABILITY_RECONNECTION_VERSION
