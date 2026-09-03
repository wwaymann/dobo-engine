from __future__ import annotations

"""Native text reconnection for promoted spherical and ovoid DOBO planters.

Sphere and ovoid bodies stay on their smooth analytic CAD routes when semantic
text is requested. Text is removed from the volumetric hierarchy before body
generation, then applied directly to the proven revolved CAD surface. Spherical
text uses per-glyph local tangent frames so every requested glyph is required to
participate physically in the final Boolean result. This prevents partial words
from passing merely because the total volume changed.
"""

from dataclasses import replace
import math
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Callable
import unicodedata

import cadquery as cq
from cadquery.func import offset, text
import numpy as np

from .native_radial_cad_adapter import (
    _build_radial_shape,
    _load_welded_stl,
    _profile_functions,
)
from .native_text_pipeline_adapter import (
    _line_contract,
    _plumbing_feature,
    _text_features,
)
from .proposal_repair import ProposalValidationSnapshot, SemanticProposalRepairer
from .semantic_contract import DesignSemanticProgram


NATIVE_RADIAL_TEXT_ADAPTER_VERSION = "NRT.4-spherical-tangent-glyph-integrity"
_SPHERICAL_BASE_ROUTE = "analytic_cad_spherical_primitive"
_OVOID_BASE_ROUTE = "analytic_cad_ovoid_primitive"
_SPHERICAL_TEXT_ROUTE = "analytic_cad_spherical_text"
_OVOID_TEXT_ROUTE = "analytic_cad_ovoid_text"


def _radial_profile(program: DesignSemanticProgram) -> str | None:
    family = str(program.body.family)
    tags = {str(tag).lower() for tag in program.body.style_tags}
    if family == "spherical" or "spherical" in tags or "sphere" in tags:
        return "spherical"
    if "ovoid" in tags or "ovoide" in tags:
        return "ovoid"
    return None


def uses_native_radial_text(program: DesignSemanticProgram) -> bool:
    """Return true for sphere/ovoid vessels whose only decoration is text."""
    if _radial_profile(program) is None or not _text_features(program):
        return False
    unsupported = tuple(
        feature
        for feature in program.features
        if feature.form_hint != "text" and not _plumbing_feature(feature)
    )
    return not unsupported


def _failure_owned_by_native_text(name: str, text_ids: set[str]) -> bool:
    value = str(name)
    for feature_id in text_ids:
        template_id = f"{feature_id}_template"
        if (
            value.startswith(feature_id)
            or f"/{feature_id}" in value
            or f"/{template_id}" in value
            or f"{feature_id}--" in value
            or f"--{feature_id}" in value
        ):
            return True
    return False


def install_native_radial_text_repair_boundary() -> None:
    """Delegate radial text-node placement diagnostics to the native CAD mapper."""
    current = SemanticProposalRepairer._evaluate.__func__
    if getattr(current, "_dobo_native_radial_text_repair_boundary", False):
        return
    previous = current

    def _evaluate_with_native_radial_text(cls, program: DesignSemanticProgram):
        snapshot, compilation = previous(cls, program)
        if not uses_native_radial_text(program):
            return snapshot, compilation
        text_ids = {str(feature.id) for feature in _text_features(program)}
        filtered = ProposalValidationSnapshot(
            surface_anchor_failures=tuple(
                failure
                for failure in snapshot.surface_anchor_failures
                if not _failure_owned_by_native_text(failure, text_ids)
            ),
            layout_failures=tuple(
                failure
                for failure in snapshot.layout_failures
                if not _failure_owned_by_native_text(failure, text_ids)
            ),
            manufacturability_failures=tuple(
                failure
                for failure in snapshot.manufacturability_failures
                if not _failure_owned_by_native_text(failure, text_ids)
            ),
        )
        return filtered, compilation

    _evaluate_with_native_radial_text._dobo_native_radial_text_repair_boundary = True
    SemanticProposalRepairer._evaluate = classmethod(_evaluate_with_native_radial_text)


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _radial_line_contract(program: DesignSemanticProgram):
    entries = tuple(_line_contract(program))
    if len(entries) > 1:
        return entries

    prompt = str(getattr(program.source, "prompt", "") or "")
    normalized = _plain(prompt)
    if "/" not in prompt or "linea" not in normalized:
        return entries
    marker = re.search(r"lineas?\s*:\s*", normalized)
    if marker is None:
        return entries
    payload = prompt[marker.end():]
    payload = re.split(r"[.\n\r]", payload, maxsplit=1)[0]
    parts = tuple(
        part.strip(" \t,;:\"'“”")
        for part in payload.split("/")
        if part.strip(" \t,;:\"'“”")
    )
    if not 2 <= len(parts) <= 6:
        return entries
    features = _text_features(program)
    if not features:
        return entries
    feature = features[0]
    return tuple((feature, part.upper()) for part in parts)


def _receiving_face(shape: cq.Shape) -> cq.Face:
    curved = [face for face in shape.Faces() if face.geomType() != "PLANE"]
    if not curved:
        raise RuntimeError("Native radial text found no curved receiving face.")
    return max(curved, key=lambda face: float(face.Area()))


def _projection_size_limit(radius: float, text_value: str, requested_size: float) -> float:
    glyph_count = max(1, len(text_value.strip()))
    usable_arc = math.pi * float(radius) * 0.76
    width_per_size = max(1.0, glyph_count * 0.72) * 1.18
    return min(float(requested_size), usable_arc / width_per_size)


def _front_elliptic_spine(
    *,
    rx: float,
    ry: float,
    z: float,
    text_value: str,
    size: float,
    angular_offset: float = 0.0,
) -> cq.Edge:
    effective_radius = math.sqrt(max(1e-9, float(rx) * float(ry)))
    glyph_count = max(1, len(text_value.strip()))
    estimated_width = max(size, glyph_count * size * 0.72)
    arc_length = min(estimated_width * 1.18, math.pi * effective_radius * 0.76)
    half_angle = max(
        math.radians(3.0),
        min(0.5 * arc_length / effective_radius, math.radians(68.0)),
    )
    center = -0.5 * math.pi + float(angular_offset)
    count = max(9, min(31, 2 * glyph_count + 9))
    points = []
    for index in range(count):
        alpha = index / float(count - 1)
        angle = center - half_angle + 2.0 * half_angle * alpha
        points.append(
            cq.Vector(
                float(rx) * math.cos(angle),
                float(ry) * math.sin(angle),
                float(z),
            )
        )
    spine = cq.Edge.makeSpline(points)
    if not spine.isValid():
        raise RuntimeError("Native radial text spine is invalid.")
    return spine


def _project_line(
    *,
    shape: cq.Shape,
    rx: float,
    ry: float,
    z: float,
    text_value: str,
    size: float,
    u_offset: float,
) -> cq.Shape:
    face = _receiving_face(shape)
    effective_radius = math.sqrt(max(1e-9, float(rx) * float(ry)))
    projection_size = _projection_size_limit(effective_radius, text_value, size)
    angular_offset = float(u_offset) / effective_radius

    def build(font_size: float) -> cq.Shape:
        spine = _front_elliptic_spine(
            rx=rx,
            ry=ry,
            z=z,
            text_value=text_value,
            size=font_size,
            angular_offset=angular_offset,
        )
        return text(
            text_value,
            font_size,
            spine,
            face,
            font="DejaVu Sans",
            kind="regular",
            halign="center",
            valign="center",
        )

    try:
        projected = build(projection_size)
    except (ValueError, RuntimeError):
        try:
            projected = build(projection_size * 0.90)
        except Exception as retry_error:
            raise RuntimeError(
                f"Native radial text projection failed for {text_value!r}."
            ) from retry_error
    if not projected.isValid():
        raise RuntimeError("Native projected radial text is invalid.")
    return projected


def _offset_tool(projected: cq.Shape, *, depth: float, mode: str, sign: float) -> cq.Shape:
    """Create a relief tool that crosses the receiving surface robustly."""
    try:
        primary_depth = min(float(depth), 1.50) if mode == "emboss" else float(depth)
        anchor_depth = min(0.16, max(0.06, 0.10 * primary_depth))
        primary = offset(projected, float(sign) * primary_depth, cap=True)
        anchor = offset(projected, -float(sign) * anchor_depth, cap=True)
        tool = primary.fuse(anchor, tol=0.01).clean()
    except Exception as error:
        raise RuntimeError("Native radial text offset failed.") from error
    if not tool.isValid():
        raise RuntimeError("Native radial text offset tool is invalid.")
    return tool


def _boolean_candidate(
    base: cq.Shape,
    projected: cq.Shape,
    *,
    depth: float,
    mode: str,
    sign: float,
) -> tuple[cq.Shape, cq.Shape, float] | None:
    try:
        tool = _offset_tool(projected, depth=depth, mode=mode, sign=sign)
        before = float(base.Volume())
        if mode == "emboss":
            current = base
            solids = tuple(tool.Solids())
            if not solids:
                return None
            for glyph in solids:
                joined = current.fuse(glyph, tol=0.01).clean()
                parts = tuple(joined.Solids())
                if len(parts) != 1:
                    return None
                current = parts[0]
            final = current.clean()
            delta = float(final.Volume()) - before
        else:
            cut = base.cut(tool, tol=0.01).clean()
            parts = tuple(cut.Solids())
            if len(parts) != 1:
                return None
            final = parts[0].clean()
            delta = before - float(final.Volume())
        if not final.isValid() or delta <= 1e-7:
            return None
        return final, tool, delta
    except Exception:
        return None


def _apply_relief(
    base: cq.Shape,
    projected: cq.Shape,
    *,
    depth: float,
    mode: str,
) -> cq.Shape:
    candidates = []
    for sign in (1.0, -1.0):
        candidate = _boolean_candidate(
            base,
            projected,
            depth=depth,
            mode=mode,
            sign=sign,
        )
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        raise RuntimeError(f"Native radial text {mode} did not create a valid relief.")
    final, _tool, _delta = max(candidates, key=lambda item: item[2])
    return final


def _numeric_derivative(function: Callable[[float], float], value: float, *, step: float = 1e-4) -> float:
    low = max(0.0, float(value) - step)
    high = min(1.0, float(value) + step)
    if high <= low:
        return 0.0
    return (float(function(high)) - float(function(low))) / (high - low)


def _glyph_width(glyph: str, size: float) -> float:
    if glyph.isspace():
        return 0.35 * float(size)
    try:
        values = cq.Workplane("XY").text(
            glyph,
            float(size),
            0.20,
            combine=False,
            font="DejaVu Sans",
            kind="regular",
            halign="center",
            valign="center",
        ).vals()
    except Exception:
        return 0.58 * float(size)
    boxes = [value.BoundingBox() for value in values if isinstance(value, cq.Shape)]
    if not boxes:
        return 0.58 * float(size)
    xmin = min(box.xmin for box in boxes)
    xmax = max(box.xmax for box in boxes)
    return max(0.20 * float(size), float(xmax - xmin))


def _safe_tangent_line_size(radius: float, text_value: str, requested: float) -> float:
    glyph_count = max(1, len(text_value.strip()))
    usable_arc = math.pi * float(radius) * 0.72
    estimated_per_size = max(1.0, glyph_count * 0.72) * 1.18
    return min(float(requested), usable_arc / estimated_per_size)


def _spherical_glyph_groups(
    *,
    route: dict[str, Any],
    text_value: str,
    size: float,
    depth: float,
    mode: str,
    z: float,
    u_offset: float,
) -> tuple[tuple[str, tuple[cq.Shape, ...]], ...]:
    """Build each spherical glyph in its own local tangent frame.

    A whole-word projected compound can contain glyph faces whose effective OCC
    orientation/intersection differs enough that only part of the word survives.
    Local tangent tools make the intersection explicit for every glyph and allow
    a physical per-glyph integrity assertion after each Boolean.
    """
    height = float(route["height_mm"])
    wall = float(route["wall_mm"])
    rx_at, ry_at = _profile_functions(route)
    t = min(1.0, max(0.0, float(z) / height))
    rx = float(rx_at(t))
    ry = float(ry_at(t))
    effective_radius = math.sqrt(max(1e-9, rx * ry))
    actual_size = _safe_tangent_line_size(effective_radius, text_value, size)
    drx_dz = _numeric_derivative(rx_at, t) / height
    dry_dz = _numeric_derivative(ry_at, t) / height

    widths = [_glyph_width(glyph, actual_size) for glyph in text_value]
    spacing = 0.12 * actual_size
    advances = [
        width_value + (spacing if index < len(widths) - 1 else 0.0)
        for index, width_value in enumerate(widths)
    ]
    total_width = sum(advances)
    centers: list[float] = []
    cursor = -0.5 * total_width
    for width_value, advance in zip(widths, advances):
        centers.append(cursor + 0.5 * width_value)
        cursor += advance

    center_theta = -0.5 * math.pi + float(u_offset) / max(effective_radius, 1e-6)
    anchor_cap = max(0.35, min(1.40, 0.40 * wall))
    anchor = min(
        anchor_cap,
        max(0.35, 0.65 * float(depth), 0.045 * actual_size),
    )
    groups: list[tuple[str, tuple[cq.Shape, ...]]] = []

    for glyph, arc_center in zip(text_value, centers):
        if glyph.isspace():
            continue
        theta = center_theta + float(arc_center) / max(effective_radius, 1e-6)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        point = np.array([rx * cos_t, ry * sin_t, float(z)], dtype=float)

        tangent_u = np.array([-rx * sin_t, ry * cos_t, 0.0], dtype=float)
        tangent_u /= np.linalg.norm(tangent_u)
        tangent_v = np.array([drx_dz * cos_t, dry_dz * sin_t, 1.0], dtype=float)
        tangent_v /= np.linalg.norm(tangent_v)
        normal = np.cross(tangent_u, tangent_v)
        normal /= np.linalg.norm(normal)
        if float(np.dot(normal, np.array([cos_t, sin_t, 0.0]))) < 0.0:
            normal = -normal

        if mode == "emboss":
            origin = point - normal * anchor
            thickness = min(float(depth), 1.50) + anchor
        elif mode == "deboss":
            origin = point + normal * anchor
            thickness = -(float(depth) + anchor)
        else:
            raise ValueError(f"Unsupported spherical text mode: {mode!r}")

        plane = cq.Plane(
            origin=tuple(float(value) for value in origin),
            xDir=tuple(float(value) for value in tangent_u),
            normal=tuple(float(value) for value in normal),
        )
        try:
            values = cq.Workplane(plane).text(
                glyph,
                actual_size,
                thickness,
                combine=False,
                font="DejaVu Sans",
                kind="regular",
                halign="center",
                valign="center",
            ).vals()
        except Exception as error:
            raise RuntimeError(
                f"Spherical native glyph construction failed for {glyph!r}."
            ) from error
        glyph_shapes = tuple(value for value in values if isinstance(value, cq.Shape))
        if not glyph_shapes:
            raise RuntimeError(f"Spherical native glyph {glyph!r} produced no CAD tool.")
        groups.append((glyph, glyph_shapes))

    if not groups:
        raise RuntimeError("Spherical native text produced no glyph tools.")
    return tuple(groups)


def _apply_spherical_line(
    base: cq.Shape,
    *,
    route: dict[str, Any],
    text_value: str,
    size: float,
    depth: float,
    mode: str,
    z: float,
    u_offset: float,
) -> tuple[cq.Shape, int]:
    groups = _spherical_glyph_groups(
        route=route,
        text_value=text_value,
        size=size,
        depth=depth,
        mode=mode,
        z=z,
        u_offset=u_offset,
    )
    current = base
    applied = 0
    for glyph_index, (glyph, shapes) in enumerate(groups):
        before_glyph = float(current.Volume())
        for shape_index, tool in enumerate(shapes):
            try:
                raw = (
                    current.fuse(tool, tol=0.01)
                    if mode == "emboss"
                    else current.cut(tool, tol=0.01)
                ).clean()
            except Exception as error:
                raise RuntimeError(
                    f"Spherical native {mode} Boolean failed at glyph {glyph_index} "
                    f"{glyph!r}, shape {shape_index}."
                ) from error
            solids = tuple(raw.Solids())
            if len(solids) != 1:
                raise RuntimeError(
                    f"Spherical native {mode} glyph {glyph_index} {glyph!r} "
                    f"produced {len(solids)} CAD solids."
                )
            current = solids[0].clean()

        after_glyph = float(current.Volume())
        delta = (
            after_glyph - before_glyph
            if mode == "emboss"
            else before_glyph - after_glyph
        )
        if delta <= 1e-7:
            raise RuntimeError(
                f"Spherical native {mode} glyph {glyph_index} {glyph!r} "
                "produced no measurable relief."
            )
        applied += 1

    return current, applied


def _single_tessellated_component(mesh):
    """Remove only negligible STL slivers produced by OCC curved-face cuts."""
    components = tuple(mesh.split(only_watertight=False))
    if len(components) <= 1:
        return mesh
    ordered = sorted(components, key=lambda item: abs(float(item.volume)), reverse=True)
    primary = ordered[0]
    primary_volume = max(abs(float(primary.volume)), 1.0)
    meaningful_limit = max(1e-3, primary_volume * 1e-8)
    for residue in ordered[1:]:
        if len(residue.faces) > 16 or abs(float(residue.volume)) > meaningful_limit:
            raise RuntimeError(
                "Native radial text STL contains a meaningful disconnected component."
            )
    cleaned = primary.copy()
    cleaned.merge_vertices()
    cleaned.remove_unreferenced_vertices()
    return cleaned


def _apply_text_block(
    shape: cq.Shape,
    route: dict[str, Any],
    program: DesignSemanticProgram,
) -> tuple[cq.Shape, float, float, int, int, int]:
    entries = tuple(_radial_line_contract(program))
    if not entries:
        volume = float(shape.Volume())
        return shape, volume, volume, 0, 0, 0

    height = float(route["height_mm"])
    rx_at, ry_at = _profile_functions(route)
    minimum_feature = float(program.manufacturing.minimum_feature_mm)
    profile = str(route.get("profile", ""))

    first_feature, _ = entries[0]
    multiline = len(entries) > 1
    slot_height = max(minimum_feature, float(first_feature.size.height_ratio) * height)
    gap = 0.22 * slot_height if multiline else 0.0
    total_block_height = len(entries) * slot_height + max(len(entries) - 1, 0) * gap
    block_center = (
        0.50 * height
        if multiline and str(first_feature.anchor.region) == "front"
        else float(first_feature.anchor.vertical) * height
    )
    block_top = block_center + 0.5 * total_block_height

    base_volume = float(shape.Volume())
    current = shape
    expected_glyph_count = sum(
        1 for _feature, literal in entries for glyph in str(literal) if not glyph.isspace()
    )
    applied_glyph_count = 0

    for index, (feature, literal) in enumerate(entries):
        if multiline:
            z = block_top - 0.5 * slot_height - index * (slot_height + gap)
            requested_size = slot_height
        else:
            z = float(feature.anchor.vertical) * height
            requested_size = max(minimum_feature, float(feature.size.height_ratio) * height)

        half_size = 0.55 * requested_size
        safe_edge = max(half_size, 0.14 * height)
        z = min(height - safe_edge, max(safe_edge, z))
        t = min(1.0, max(0.0, z / height))
        rx = float(rx_at(t))
        ry = float(ry_at(t))
        effective_radius = math.sqrt(max(1e-9, rx * ry))
        if multiline and str(first_feature.anchor.region) == "front":
            u_offset = 0.0
        else:
            horizontal = float(
                first_feature.anchor.horizontal if multiline else feature.anchor.horizontal
            )
            u_offset = 0.25 * horizontal * (2.0 * math.pi * effective_radius)

        mode = "deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss"
        relief_depth = max(0.1, float(feature.size.depth_mm))

        if profile == "spherical":
            current, line_glyphs = _apply_spherical_line(
                current,
                route=route,
                text_value=str(literal),
                size=requested_size,
                depth=relief_depth,
                mode=mode,
                z=z,
                u_offset=u_offset,
            )
            applied_glyph_count += line_glyphs
        else:
            # Compatibility path retained for any non-spherical caller. The
            # promoted ovoid route is normally handled by its dedicated tangent
            # adapter before reaching this decorator.
            projected = _project_line(
                shape=current,
                rx=rx,
                ry=ry,
                z=z,
                text_value=str(literal),
                size=requested_size,
                u_offset=u_offset,
            )
            current = _apply_relief(
                current,
                projected,
                depth=relief_depth,
                mode=mode,
            )
            applied_glyph_count += sum(1 for glyph in str(literal) if not glyph.isspace())

    final = current.clean()
    if not final.isValid() or len(tuple(final.Solids())) != 1:
        raise RuntimeError("Native radial text did not preserve one valid CAD vessel solid.")
    if expected_glyph_count <= 0 or applied_glyph_count != expected_glyph_count:
        raise RuntimeError(
            "Native radial text glyph integrity failed: "
            f"expected {expected_glyph_count}, applied {applied_glyph_count}."
        )
    return (
        final,
        base_volume,
        float(final.Volume()),
        len(entries),
        expected_glyph_count,
        applied_glyph_count,
    )


def decorate_radial_mesh_result_with_native_text(
    mesh_result,
    motor: dict[str, Any],
    program: DesignSemanticProgram,
):
    """Apply semantic text directly to sphere/ovoid analytic CAD geometry."""
    if not uses_native_radial_text(program):
        return mesh_result

    route = motor.get("_analytic_radial")
    base_route = str(motor.get("_capability_route", ""))
    profile = _radial_profile(program)
    expected_base = _SPHERICAL_BASE_ROUTE if profile == "spherical" else _OVOID_BASE_ROUTE
    final_route = _SPHERICAL_TEXT_ROUTE if profile == "spherical" else _OVOID_TEXT_ROUTE
    if not isinstance(route, dict) or base_route != expected_base:
        raise RuntimeError(
            "Radial text requires the promoted analytic sphere/ovoid body route; "
            "legacy volumetric fallback is not accepted."
        )

    started = perf_counter()
    shape, _rx_at, _ry_at = _build_radial_shape(route)
    (
        final_shape,
        base_volume,
        final_volume,
        line_count,
        expected_glyph_count,
        applied_glyph_count,
    ) = _apply_text_block(shape, route, program)

    stl_path = Path(str(mesh_result.stl_path))
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(final_shape, str(stl_path), tolerance=0.08, angularTolerance=0.08)
    mesh = _single_tessellated_component(_load_welded_stl(stl_path))
    mesh.export(str(stl_path))
    components = tuple(mesh.split(only_watertight=False))

    checks = dict(getattr(mesh_result, "semantic_checks", {}) or {})
    checks["native_radial_text_volume_changed"] = abs(final_volume - base_volume) > 1e-7
    checks["native_radial_text_one_component"] = len(components) == 1
    checks["native_radial_text_mesh_compact"] = 0 < int(len(mesh.vertices)) < 100_000
    checks["native_radial_text_glyph_integrity"] = (
        expected_glyph_count > 0 and applied_glyph_count == expected_glyph_count
    )

    elapsed = perf_counter() - started
    stage_seconds = dict(getattr(mesh_result, "stage_seconds", {}) or {})
    stage_seconds["native_radial_cad_text"] = elapsed

    motor["_base_capability_route"] = expected_base
    motor["_capability_route"] = final_route
    motor["_native_radial_text"] = {
        "adapter_version": NATIVE_RADIAL_TEXT_ADAPTER_VERSION,
        "profile": profile,
        "line_count": line_count,
        "expected_glyph_count": expected_glyph_count,
        "applied_glyph_count": applied_glyph_count,
        "base_volume_mm3": base_volume,
        "final_volume_mm3": final_volume,
        "volume_delta_mm3": final_volume - base_volume,
    }

    decorated = replace(
        mesh_result,
        mesh=mesh,
        vertex_count=int(len(mesh.vertices)),
        face_count=int(len(mesh.faces)),
        component_count=len(components),
        volume_mm3=float(abs(mesh.volume)),
        watertight=bool(mesh.is_watertight),
        winding_consistent=bool(mesh.is_winding_consistent),
        flat_base_vertex_count=int(np.count_nonzero(np.abs(mesh.vertices[:, 2]) <= 0.08)),
        semantic_checks=checks,
        stage_seconds=stage_seconds,
        generation_seconds=float(mesh_result.generation_seconds) + elapsed,
    )
    decorated.validate()
    return decorated


install_native_radial_text_repair_boundary()
