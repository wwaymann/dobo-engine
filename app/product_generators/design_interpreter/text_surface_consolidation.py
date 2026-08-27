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


TEXT_SURFACE_CONSOLIDATION_VERSION = "C0R.6.3-multiline-fidelity-vessel-safe"
_INSTALLED = False

# Do not capture GeneralBodyFamilyExpander.apply here. This module is imported
# before install_core_capability_reconnection() runs from package __init__, so a
# module-level snapshot would point at the pre-C0R implementation and silently
# bypass real glyph reconnection, restoring the old rounded-box plaque.
_PREVIOUS_PLACED_FIELD = HierarchicalFeatureVesselEngine._placed_field.__func__


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _prompt_lines(prompt: str | None) -> tuple[str, ...]:
    """Extract explicit N-line text without depending on model feature splitting."""
    if not prompt:
        return ()
    raw = str(prompt)

    # Accept a quoted text block containing either real newlines or the literal
    # two-character sequence ``\\n`` used by the Capability Lab prompt box.
    for match in re.finditer(r'[\"“”]([^\"“”]+)[\"“”]', raw, flags=re.DOTALL):
        payload = match.group(1)
        if "\\n" in payload or "\n" in payload:
            normalized = payload.replace("\\r\\n", "\n").replace("\\n", "\n")
            lines = tuple(part.strip() for part in normalized.splitlines() if part.strip())
            if len(lines) >= 2:
                return tuple(line.upper() for line in lines)

    # Explicit assignments are the strongest contract:
    # línea 1 = "PLANTA"; línea 2 = "UNA"; línea 3 = "IDEA".
    assignment = re.compile(
        r"(?:linea|línea)\s*(\d+)\s*(?:=|:)\s*[\"'“”]?\s*(.*?)\s*[\"'“”]?\s*"
        r"(?=(?:;|,)?\s*(?:linea|línea)\s*\d+\s*(?:=|:)|(?:[.;]\s*)?$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    matches = assignment.findall(raw)
    if matches:
        ordered = sorted(
            (int(index), text.strip(" .;,:\"'“”"))
            for index, text in matches
            if text.strip(" .;,:\"'“”")
        )
        if len(ordered) >= 2:
            return tuple(text.upper() for _, text in ordered)
    return ()


def _plumbing_name(value: object) -> bool:
    normalized = _plain(str(value)).replace("-", "_").replace(" ", "_")
    tokens = set(filter(None, normalized.split("_")))
    return bool(tokens & {
        "drain", "drainage", "drenaje", "drenajeinferior",
        "opening", "abertura", "boca", "cavity", "cavidad", "hueco", "hollow",
    })


def _plumbing_feature(feature) -> bool:
    if getattr(feature, "form_hint", None) == "text":
        return False
    return _plumbing_name(getattr(feature, "concept", "")) or _plumbing_name(
        getattr(feature, "id", "")
    )


def _remove_plumbing_helpers(motor_program, program) -> None:
    """Remove helper geometry for vessel-owned opening/cavity/drain semantics."""
    hierarchy = motor_program.get("hierarchy_program")
    if not isinstance(hierarchy, dict):
        return

    remove_ids = {str(feature.id) for feature in program.features if _plumbing_feature(feature)}
    remove_templates = {f"{feature_id}_template" for feature_id in remove_ids}

    def helper_node(node: dict) -> bool:
        node_id = str(node.get("id", ""))
        template_ids = {str(value) for value in node.get("template_ids", [])}
        return (
            node_id in remove_ids
            or _plumbing_name(node_id)
            or bool(template_ids & remove_templates)
            or any(_plumbing_name(value) for value in template_ids)
        )

    def prune(node: dict):
        if helper_node(node):
            return None
        cleaned = dict(node)
        children = []
        for child in node.get("children", []):
            if not isinstance(child, dict):
                children.append(child)
                continue
            kept = prune(child)
            if kept is not None:
                children.append(kept)
        cleaned["children"] = children
        return cleaned

    cleaned_roots = []
    for root in hierarchy.get("roots", []):
        if not isinstance(root, dict):
            cleaned_roots.append(root)
            continue
        kept = prune(root)
        if kept is not None:
            cleaned_roots.append(kept)
    hierarchy["roots"] = cleaned_roots

    hierarchy["templates"] = [
        template
        for template in hierarchy.get("templates", [])
        if not isinstance(template, dict)
        or (
            str(template.get("id", "")) not in remove_templates
            and not _plumbing_name(template.get("id", ""))
            and not _plumbing_name(template.get("semantic_kind", ""))
        )
    ]


def _minimum_safe_text_blend(hierarchy: dict) -> float:
    manufacturability = hierarchy.get("feature_manufacturability")
    proportional = hierarchy.get("proportional_scaling")
    minimum_blend = 0.4
    minimum_scale = 1.0
    if isinstance(manufacturability, dict):
        minimum_blend = max(
            1e-6,
            float(manufacturability.get("minimum_blend_mm", minimum_blend)),
        )
    if isinstance(proportional, dict):
        minimum_scale = max(
            1e-6,
            float(proportional.get("minimum_scale", minimum_scale)),
        )
    # Manufacturability validates blend after the placement scale is applied.
    return 1.01 * minimum_blend / minimum_scale


def _remove_extra_text_features(hierarchy: dict, keep_feature_id: str, extra_ids: set[str]) -> None:
    if not extra_ids:
        return
    extra_templates = {f"{feature_id}_template" for feature_id in extra_ids}

    def prune(node: dict):
        node_id = str(node.get("id", ""))
        template_ids = {str(value) for value in node.get("template_ids", [])}
        if node_id in extra_ids or bool(template_ids & extra_templates):
            return None
        cleaned = dict(node)
        cleaned["children"] = [
            kept
            for child in node.get("children", [])
            if isinstance(child, dict)
            for kept in (prune(child),)
            if kept is not None
        ]
        return cleaned

    hierarchy["roots"] = [
        kept
        for root in hierarchy.get("roots", [])
        if isinstance(root, dict)
        for kept in (prune(root),)
        if kept is not None
    ]
    hierarchy["templates"] = [
        template
        for template in hierarchy.get("templates", [])
        if not isinstance(template, dict)
        or str(template.get("id", "")) not in extra_templates
    ]
    for template_id in extra_templates:
        _core._TEXT_TEMPLATES.pop(template_id, None)
        _core._TEXT_WRAP_RADIUS.pop(template_id, None)


def _apply_consolidated(cls, motor_program, program):
    # Always extend the promoted C0R text contract directly. Calling a captured
    # pre-install apply here regresses text back to the generic rounded_box.
    result = _core._apply_with_text_contract(cls, motor_program, program)
    text_features = tuple(feature for feature in program.features if feature.form_hint == "text")
    if not text_features:
        return result

    source = getattr(program, "source", None)
    lines = _prompt_lines(getattr(source, "prompt", None))
    hierarchy = motor_program.get("hierarchy_program", {})

    if lines:
        # Explicit multiline syntax is one text block, even when the semantic
        # model independently emitted several text features. Keep the first
        # anchor and suppress the redundant model-generated text nodes.
        text_feature = text_features[0]
        extra_ids = {str(feature.id) for feature in text_features[1:]}
        if isinstance(hierarchy, dict):
            _remove_extra_text_features(hierarchy, str(text_feature.id), extra_ids)

        template_id = f"{text_feature.id}_template"
        literal = "\n".join(lines)
        _core._TEXT_TEMPLATES[template_id] = literal
        _core._TEXT_TEMPLATES[str(text_feature.id)] = literal
        if isinstance(hierarchy, dict):
            for template in hierarchy.get("templates", []):
                if isinstance(template, dict) and str(template.get("id")) == template_id:
                    template["text_literal"] = literal
                    template["text_lines"] = list(lines)
                    template["semantic_kind"] = "text_glyph_contour_multiline"

    # The glyph SDF remains cached and fast. Visible faceting is dominated by
    # the final 3D lattice, so improve that lattice rather than reintroducing the
    # six-minute per-triangle glyph path. 0.45 mm is intentionally conservative:
    # noticeably finer than C0R.6.2 while still using the cached field route.
    grid = motor_program.get("grid")
    if isinstance(grid, dict):
        grid["voxel_mm"] = min(float(grid.get("voxel_mm", 1.0)), 0.45)
    if isinstance(hierarchy, dict):
        refinement = hierarchy.get("adaptive_refinement")
        if isinstance(refinement, dict):
            refinement["detail_subdivision_passes"] = max(
                3, int(refinement.get("detail_subdivision_passes", 0))
            )
        safe_text_blend = _minimum_safe_text_blend(hierarchy)
        for template in hierarchy.get("templates", []):
            if isinstance(template, dict) and str(template.get("id")) in _core._TEXT_TEMPLATES:
                template["blend_mm"] = safe_text_blend

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

    # Develop the actual cylindrical receiving surface into arc length. Depth is
    # radial distance from that same surface, so every glyph sample follows the
    # local cylindrical normal instead of a guessed planar normal.
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
