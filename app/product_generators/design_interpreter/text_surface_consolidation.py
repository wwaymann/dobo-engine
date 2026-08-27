from __future__ import annotations

"""Final text/surface consolidation layer for the promoted DOBO core.

This module deliberately extends the existing C0R reconnection instead of
introducing a second text engine. It preserves the cached real-glyph SDF path,
adds explicit N-line layout, increases final spatial fidelity for text-bearing
parts, and removes semantic plumbing features already owned by the vessel
(opening/cavity/drain) so they cannot survive as visible helper geometry.
"""

import re
import unicodedata

import numpy as np

from . import core_capability_reconnection as _core
from .body_family_expansion import GeneralBodyFamilyExpander
from product_generators.organic_shapes.hierarchy_engine import HierarchicalFeatureVesselEngine


TEXT_SURFACE_CONSOLIDATION_VERSION = "C0R.6-multiline-surface-quality"
_INSTALLED = False

_PREVIOUS_APPLY = GeneralBodyFamilyExpander.apply.__func__
_PREVIOUS_PLACED_FIELD = HierarchicalFeatureVesselEngine._placed_field.__func__


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _prompt_lines(prompt: str | None) -> tuple[str, ...]:
    """Extract explicit line assignments without guessing paragraph structure."""
    if not prompt:
        return ()
    normalized = str(prompt).replace("\r", " ").replace("\n", " ")
    matches = re.findall(
        r"(?:linea|línea)\s*(\d+)\s*(?:=|:)[\s\"'“”]*([^;\"'“”]+?)(?=(?:\s*;\s*|\s+)(?:linea|línea)\s*\d+\s*(?:=|:)|[\"'“”]*\s*[.;]?$)",
        normalized,
        flags=re.IGNORECASE,
    )
    if not matches:
        return ()
    ordered = sorted((int(index), text.strip(" .;,:\"'“”")) for index, text in matches)
    return tuple(text.upper() for _, text in ordered if text.strip())


def _plumbing_feature(feature) -> bool:
    if getattr(feature, "form_hint", None) == "text":
        return False
    tokens = set(_plain(getattr(feature, "concept", "")).replace("-", "_").split("_"))
    tokens.update(_plain(getattr(feature, "id", "")).replace("-", "_").split("_"))
    return bool(tokens & {
        "drain", "drainage", "drenaje", "drenajeinferior",
        "opening", "abertura", "boca", "cavity", "cavidad", "hueco", "hollow",
    })


def _remove_plumbing_helpers(motor_program, program) -> None:
    hierarchy = motor_program.get("hierarchy_program")
    if not isinstance(hierarchy, dict):
        return
    remove_ids = {feature.id for feature in program.features if _plumbing_feature(feature)}
    if not remove_ids:
        return
    remove_templates = {f"{feature_id}_template" for feature_id in remove_ids}
    hierarchy["roots"] = [
        node for node in hierarchy.get("roots", [])
        if not isinstance(node, dict) or str(node.get("id")) not in remove_ids
    ]
    hierarchy["templates"] = [
        template for template in hierarchy.get("templates", [])
        if not isinstance(template, dict) or str(template.get("id")) not in remove_templates
    ]


def _apply_consolidated(cls, motor_program, program):
    result = _PREVIOUS_APPLY(cls, motor_program, program)
    text_features = tuple(feature for feature in program.features if feature.form_hint == "text")
    if not text_features:
        return result

    # Explicit line syntax is a structural text contract. Preserve it as N lines
    # rather than relying on the semantic model to invent N unrelated features.
    source = getattr(program, "source", None)
    lines = _prompt_lines(getattr(source, "prompt", None))
    if lines:
        text_feature = text_features[0]
        template_id = f"{text_feature.id}_template"
        literal = "\n".join(lines)
        _core._TEXT_TEMPLATES[template_id] = literal
        hierarchy = motor_program.get("hierarchy_program", {})
        for template in hierarchy.get("templates", []):
            if isinstance(template, dict) and str(template.get("id")) == template_id:
                template["text_literal"] = literal
                template["text_lines"] = list(lines)
                template["semantic_kind"] = "text_glyph_contour_multiline"

    # The 256px glyph cache already contains ample contour detail. The visible
    # faceting came from the final 3D voxel lattice, so refine that lattice rather
    # than making the SDF slower. 0.55 mm is the compiler's established lower
    # quality bound and keeps the fast cached-field route practical.
    grid = motor_program.get("grid")
    if isinstance(grid, dict):
        grid["voxel_mm"] = min(float(grid.get("voxel_mm", 1.0)), 0.55)
    hierarchy = motor_program.get("hierarchy_program")
    if isinstance(hierarchy, dict):
        refinement = hierarchy.get("adaptive_refinement")
        if isinstance(refinement, dict):
            refinement["detail_subdivision_passes"] = max(
                2, int(refinement.get("detail_subdivision_passes", 0))
            )
        # Large smooth-union radii soften and destroy glyph corners. Text needs
        # contact with the wall, not a plaque-like morphological flare.
        for template in hierarchy.get("templates", []):
            if isinstance(template, dict) and str(template.get("id")) in _core._TEXT_TEMPLATES:
                template["blend_mm"] = min(float(template.get("blend_mm", 0.35)), 0.35)

    _remove_plumbing_helpers(motor_program, program)
    return result


def _multiline_font_field(feature, text: str, u, depth_coordinate, v):
    lines = tuple(line.strip() for line in str(text).splitlines() if line.strip())
    if len(lines) <= 1:
        return _core._font_text_field(feature, text, u, depth_coordinate, v)
    half_sizes = feature.half_sizes
    if half_sizes is None:
        return _core._font_text_field(feature, " ".join(lines), u, depth_coordinate, v)

    total_width = 2.0 * float(half_sizes[0])
    total_height = 2.0 * float(half_sizes[2])
    half_depth = float(half_sizes[1])
    line_gap_ratio = 0.22
    slot_height = total_height / (len(lines) + line_gap_ratio * (len(lines) - 1))
    gap = line_gap_ratio * slot_height
    top = 0.5 * total_height
    fields = []

    for index, line in enumerate(lines):
        _, _, _, _, _, natural_width, natural_height = _core._glyph_sdf(line)
        scale = min(total_width / natural_width, slot_height / natural_height)
        center_v = top - 0.5 * slot_height - index * (slot_height + gap)
        planar = _core._sample_glyph_sdf(
            line,
            np.asarray(u) / scale,
            (np.asarray(v) - center_v) / scale,
        ) * scale
        fields.append(_core._extruded_2d_distance(planar, depth_coordinate, half_depth))

    result = fields[0]
    for field in fields[1:]:
        result = np.minimum(result, field)
    return result


def _placed_field_consolidated(cls, placement, x, y, z):
    text = _core._TEXT_TEMPLATES.get(placement.feature.id)
    radius = _core._TEXT_WRAP_RADIUS.get(placement.feature.id)
    if not text or radius is None or radius <= 0.0:
        return _PREVIOUS_PLACED_FIELD(cls, placement, x, y, z)

    matrix = np.asarray(placement.matrix, dtype=np.float64)
    origin = matrix[:3, 3]
    tangent_column = matrix[:3, 0]
    inward_column = matrix[:3, 1]
    vertical_column = matrix[:3, 2]
    scale_u = max(float(np.linalg.norm(tangent_column)), 1e-12)
    scale_n = max(float(np.linalg.norm(inward_column)), 1e-12)
    scale_v = max(float(np.linalg.norm(vertical_column)), 1e-12)
    tangent = tangent_column / scale_u
    outward = -inward_column / scale_n
    vertical = vertical_column / scale_v

    # Develop the *actual cylindrical receiving surface* into arc-length u.
    # Depth is radial distance from that same surface, so every glyph sample has
    # the same contact rule; edge letters no longer use a guessed planar normal.
    center_x = float(origin[0] - outward[0] * radius)
    center_y = float(origin[1] - outward[1] * radius)
    dx = x - center_x
    dy = y - center_y
    radial_distance = np.sqrt(dx * dx + dy * dy)
    normal_projection = dx * outward[0] + dy * outward[1]
    tangent_projection = dx * tangent[0] + dy * tangent[1]
    angle = np.arctan2(tangent_projection, normal_projection)
    u = radius * angle / scale_u
    depth_coordinate = (radial_distance - radius) / scale_n

    world_dx = x - float(origin[0])
    world_dy = y - float(origin[1])
    world_dz = z - float(origin[2])
    v = (world_dx * vertical[0] + world_dy * vertical[1] + world_dz * vertical[2]) / scale_v

    return _multiline_font_field(
        placement.feature, text, u, depth_coordinate, v
    ) * placement.distance_scale


def install_text_surface_consolidation() -> str:
    global _INSTALLED
    if _INSTALLED:
        return TEXT_SURFACE_CONSOLIDATION_VERSION
    GeneralBodyFamilyExpander.apply = classmethod(_apply_consolidated)
    HierarchicalFeatureVesselEngine._placed_field = classmethod(_placed_field_consolidated)
    _INSTALLED = True
    return TEXT_SURFACE_CONSOLIDATION_VERSION
