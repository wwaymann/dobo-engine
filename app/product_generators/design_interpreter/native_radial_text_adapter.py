from __future__ import annotations

"""Native text reconnection for promoted radial DOBO planters.

The spherical planter keeps its approved analytic CAD body. Text is removed from
the volumetric hierarchy before body generation and is then rebuilt as physical
CAD relief against the proven curved surface.

A projected OCC text face proved insufficient for production quality: individual
strokes could offset in inconsistent directions, and large tangent glyphs could
intersect the sphere only near their centres. The spherical route therefore uses
one local tangent prism per glyph and clips it against paired analytic surface
bands generated from the pristine outer REVOLUTION face. The outward/inward band
pieces are fused only after they have been locally clipped by a glyph. This
avoids a fragile whole-surface fuse while still giving every emboss/deboss tool
a physical overlap across the curved vessel skin.

For multiline text, typography is laid out as one coherent block before mapping
the lines to the sphere: every line shares one capped type size, one common front
centre and a fixed line advance. This prevents large semantic height ratios from
spreading the three lines into high-curvature zones where the words cease to read
as a single horizontal block.

The CAD result is authoritative: it must contain exactly one valid solid before
export. OCC tessellation can nevertheless leave seam slivers or split a relief
patch at a coarse STL tolerance, especially for multiline spherical text. Export
therefore retries with progressively finer tessellation before classifying a
secondary STL component as a real geometry failure.

The promoted ovoid keeps its dedicated adapter. This module retains the shared
radial helpers used by that adapter and owns the spherical text decorator.
"""

from dataclasses import replace
import math
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Callable
import unicodedata

import cadquery as cq
from cadquery.func import offset
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


NATIVE_RADIAL_TEXT_ADAPTER_VERSION = "NRT.10-stronger-spherical-emboss"
_SPHERICAL_BASE_ROUTE = "analytic_cad_spherical_primitive"
_OVOID_BASE_ROUTE = "analytic_cad_ovoid_primitive"
_SPHERICAL_TEXT_ROUTE = "analytic_cad_spherical_text"
_OVOID_TEXT_ROUTE = "analytic_cad_ovoid_text"
_SPHERICAL_FONT = "DejaVu Sans"
_SPHERICAL_FONT_KIND = "bold"
_SPHERICAL_MAX_TEXT_MM = 30.0
_SPHERICAL_MULTILINE_MAX_TEXT_MM = 22.0
_SPHERICAL_MULTILINE_GAP_RATIO = 0.30
_SPHERICAL_MULTILINE_FRONT_CENTER = 0.55


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


def _numeric_derivative(
    function: Callable[[float], float],
    value: float,
    *,
    step: float = 1e-4,
) -> float:
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
            font=_SPHERICAL_FONT,
            kind=_SPHERICAL_FONT_KIND,
            halign="center",
            valign="center",
        ).vals()
    except Exception:
        return 0.62 * float(size)
    boxes = [value.BoundingBox() for value in values if isinstance(value, cq.Shape)]
    if not boxes:
        return 0.62 * float(size)
    xmin = min(box.xmin for box in boxes)
    xmax = max(box.xmax for box in boxes)
    return max(0.20 * float(size), float(xmax - xmin))


def _safe_spherical_line_size(
    radius: float,
    text_value: str,
    requested: float,
) -> float:
    glyph_count = max(1, len(text_value.strip()))
    usable_arc = math.pi * float(radius) * 0.72
    estimated_per_size = max(1.0, glyph_count * 0.72) * 1.18
    return min(
        float(requested),
        _SPHERICAL_MAX_TEXT_MM,
        usable_arc / estimated_per_size,
    )


def _multiline_block_metrics(
    entries,
    *,
    route: dict[str, Any],
    minimum_feature: float,
) -> tuple[float, float, tuple[float, ...]]:
    """Lay out multiline text as one centred typographic block.

    The semantic feature height may scale to 40+ mm on a 300 mm sphere while the
    actual spherical text size is capped at 30 mm. Using the semantic height for
    line spacing therefore pushes the first/last line into much steeper surface
    zones. We instead choose one shared size from the longest line at the block
    centre, then derive all vertical positions from that physical type size.
    """
    height = float(route["height_mm"])
    rx_at, ry_at = _profile_functions(route)
    first_feature, _ = entries[0]
    requested = max(
        float(minimum_feature),
        float(first_feature.size.height_ratio) * height,
    )
    front_block = str(first_feature.anchor.region) == "front"
    center_ratio = (
        _SPHERICAL_MULTILINE_FRONT_CENTER
        if front_block
        else float(first_feature.anchor.vertical)
    )
    center_ratio = min(0.72, max(0.28, center_ratio))
    center_z = center_ratio * height
    center_t = center_z / height
    center_radius = math.sqrt(
        max(
            1e-9,
            float(rx_at(center_t)) * float(ry_at(center_t)),
        )
    )
    longest = max((str(literal) for _feature, literal in entries), key=len)
    shared_size = _safe_spherical_line_size(
        center_radius,
        longest,
        requested,
    )
    shared_size = max(
        float(minimum_feature),
        min(shared_size, _SPHERICAL_MULTILINE_MAX_TEXT_MM),
    )
    line_advance = shared_size * (1.0 + _SPHERICAL_MULTILINE_GAP_RATIO)
    midpoint = 0.5 * (len(entries) - 1)
    line_z = tuple(
        center_z + (midpoint - index) * line_advance
        for index in range(len(entries))
    )
    safe_edge = max(0.60 * shared_size, 0.16 * height)
    line_z = tuple(
        min(height - safe_edge, max(safe_edge, value))
        for value in line_z
    )
    return shared_size, center_z, line_z


def _outer_revolution_face(shape: cq.Shape) -> cq.Face:
    revolved = [face for face in shape.Faces() if face.geomType() == "REVOLUTION"]
    if not revolved:
        raise RuntimeError("Spherical native text found no outer REVOLUTION face.")
    return max(revolved, key=lambda face: float(face.Area()))


def _radial_extent(shape: cq.Shape) -> float:
    box = shape.BoundingBox()
    return max(
        abs(float(box.xmin)),
        abs(float(box.xmax)),
        abs(float(box.ymin)),
        abs(float(box.ymax)),
    )


def _outward_offset_sign(face: cq.Face) -> float:
    """Determine OCC offset orientation from geometry instead of assuming it."""
    probe = 0.25
    try:
        positive = offset(face, probe, cap=True)
        negative = offset(face, -probe, cap=True)
    except Exception as error:
        raise RuntimeError("Spherical surface-band orientation probe failed.") from error
    positive_extent = _radial_extent(positive)
    negative_extent = _radial_extent(negative)
    if abs(positive_extent - negative_extent) <= 1e-6:
        raise RuntimeError("Spherical surface-band orientation is ambiguous.")
    return 1.0 if positive_extent > negative_extent else -1.0


def _surface_band_parts(
    pristine: cq.Shape,
    *,
    requested_depth: float,
    mode: str,
) -> tuple[cq.Shape, cq.Shape, float]:
    """Build paired curved band solids without fusing the complete sphere skin."""
    face = _outer_revolution_face(pristine)
    outward_sign = _outward_offset_sign(face)
    if mode == "emboss":
        depth = min(max(float(requested_depth), 2.40), 2.80)
        primary_distance = outward_sign * depth
        anchor_distance = -outward_sign * 0.22
    elif mode == "deboss":
        depth = min(max(float(requested_depth), 1.00), 1.60)
        primary_distance = -outward_sign * depth
        anchor_distance = outward_sign * 0.18
    else:
        raise ValueError(f"Unsupported spherical text mode: {mode!r}")

    try:
        primary = offset(face, primary_distance, cap=True)
        anchor = offset(face, anchor_distance, cap=True)
    except Exception as error:
        raise RuntimeError(f"Spherical native {mode} surface bands failed.") from error
    if (
        not primary.isValid()
        or not anchor.isValid()
        or not tuple(primary.Solids())
        or not tuple(anchor.Solids())
    ):
        raise RuntimeError(f"Spherical native {mode} surface band part is invalid.")
    return primary, anchor, depth


def _glyph_centres(
    text_value: str,
    size: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    widths = tuple(
        _glyph_width(glyph, size) if not glyph.isspace() else 0.35 * size
        for glyph in text_value
    )
    spacing = 0.12 * float(size)
    advances = tuple(
        width + (spacing if index < len(widths) - 1 else 0.0)
        for index, width in enumerate(widths)
    )
    cursor = -0.5 * sum(advances)
    centres: list[float] = []
    for width, advance in zip(widths, advances):
        centres.append(cursor + 0.5 * width)
        cursor += advance
    return widths, tuple(centres)


def _apply_spherical_line(
    current: cq.Shape,
    *,
    pristine: cq.Shape,
    route: dict[str, Any],
    text_value: str,
    size: float,
    mode: str,
    z: float,
    u_offset: float,
    surface_band_parts: tuple[cq.Shape, cq.Shape, float],
) -> tuple[cq.Shape, int]:
    height = float(route["height_mm"])
    rx_at, ry_at = _profile_functions(route)
    t = min(1.0, max(0.0, float(z) / height))
    rx = float(rx_at(t))
    ry = float(ry_at(t))
    effective_radius = math.sqrt(max(1e-9, rx * ry))
    actual_size = _safe_spherical_line_size(effective_radius, text_value, size)
    drx_dz = _numeric_derivative(rx_at, t) / height
    dry_dz = _numeric_derivative(ry_at, t) / height
    widths, centres = _glyph_centres(text_value, actual_size)
    primary_band, anchor_band, effective_depth = surface_band_parts

    center_theta = -0.5 * math.pi + float(u_offset) / max(effective_radius, 1e-6)
    applied = 0

    for glyph_index, (glyph, arc_center, glyph_width) in enumerate(
        zip(text_value, centres, widths)
    ):
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

        half_diagonal = 0.5 * math.sqrt(float(glyph_width) ** 2 + float(actual_size) ** 2)
        conservative_radius = max(half_diagonal + 1e-3, min(effective_radius, 0.5 * height))
        sagitta = conservative_radius - math.sqrt(
            max(0.0, conservative_radius**2 - half_diagonal**2)
        )
        inward_span = sagitta + effective_depth + 0.80
        total_span = inward_span + effective_depth + 1.20
        plane = cq.Plane(
            origin=tuple(float(value) for value in point - normal * inward_span),
            xDir=tuple(float(value) for value in tangent_u),
            normal=tuple(float(value) for value in normal),
        )

        try:
            values = cq.Workplane(plane).text(
                glyph,
                actual_size,
                total_span,
                combine=False,
                font=_SPHERICAL_FONT,
                kind=_SPHERICAL_FONT_KIND,
                halign="center",
                valign="center",
            ).vals()
        except Exception as error:
            raise RuntimeError(f"Spherical native glyph construction failed for {glyph!r}.") from error

        prisms = tuple(value for value in values if isinstance(value, cq.Shape))
        if not prisms:
            raise RuntimeError(f"Spherical native glyph {glyph!r} produced no CAD prism.")

        before_glyph = float(current.Volume())
        for prism_index, prism in enumerate(prisms):
            try:
                clipped_primary = prism.intersect(primary_band, tol=0.01).clean()
                clipped_anchor = prism.intersect(anchor_band, tol=0.01).clean()
            except Exception as error:
                raise RuntimeError(
                    f"Spherical native {mode} clipping failed at glyph {glyph_index} {glyph!r}, prism {prism_index}."
                ) from error

            if not clipped_primary.isValid() or float(clipped_primary.Volume()) <= 1e-7:
                raise RuntimeError(
                    f"Spherical native {mode} glyph {glyph_index} {glyph!r} did not intersect the primary curved surface band."
                )

            try:
                if clipped_anchor.isValid() and float(clipped_anchor.Volume()) > 1e-7:
                    tool = clipped_primary.fuse(clipped_anchor, tol=0.01).clean()
                else:
                    tool = clipped_primary
            except Exception as error:
                raise RuntimeError(
                    f"Spherical native {mode} local band fusion failed at glyph {glyph_index} {glyph!r}, prism {prism_index}."
                ) from error

            if not tool.isValid() or float(tool.Volume()) <= 1e-7:
                raise RuntimeError(
                    f"Spherical native {mode} glyph {glyph_index} {glyph!r} produced an invalid local relief tool."
                )

            try:
                raw = (
                    current.fuse(tool, tol=0.01)
                    if mode == "emboss"
                    else current.cut(tool, tol=0.01)
                ).clean()
            except Exception as error:
                raise RuntimeError(
                    f"Spherical native {mode} Boolean failed at glyph {glyph_index} {glyph!r}, prism {prism_index}."
                ) from error
            solids = tuple(raw.Solids())
            if len(solids) != 1:
                raise RuntimeError(
                    f"Spherical native {mode} glyph {glyph_index} {glyph!r} produced {len(solids)} CAD solids."
                )
            current = solids[0].clean()

        after_glyph = float(current.Volume())
        delta = after_glyph - before_glyph if mode == "emboss" else before_glyph - after_glyph
        if delta <= 1e-7:
            raise RuntimeError(
                f"Spherical native {mode} glyph {glyph_index} {glyph!r} produced no measurable relief."
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
            raise RuntimeError("Native radial text STL contains a meaningful disconnected component.")
    cleaned = primary.copy()
    cleaned.merge_vertices()
    cleaned.remove_unreferenced_vertices()
    return cleaned


def _export_connected_spherical_text(final_shape: cq.Shape, stl_path: Path):
    """Export a one-solid CAD result and retry only STL tessellation if needed."""
    profiles = (
        (0.06, 0.07),
        (0.04, 0.05),
        (0.025, 0.035),
    )
    last_error: RuntimeError | None = None
    for tolerance, angular_tolerance in profiles:
        cq.exporters.export(
            final_shape,
            str(stl_path),
            tolerance=tolerance,
            angularTolerance=angular_tolerance,
        )
        mesh = _load_welded_stl(stl_path)
        try:
            connected = _single_tessellated_component(mesh)
        except RuntimeError as error:
            last_error = error
            continue
        connected.export(str(stl_path))
        return connected, tolerance, angular_tolerance
    raise RuntimeError(
        "Native radial text STL remained disconnected after fine tessellation retries."
    ) from last_error


def _apply_text_block(
    shape: cq.Shape,
    route: dict[str, Any],
    program: DesignSemanticProgram,
) -> tuple[cq.Shape, float, float, int, int, int]:
    entries = tuple(_radial_line_contract(program))
    if not entries:
        volume = float(shape.Volume())
        return shape, volume, volume, 0, 0, 0

    profile = str(route.get("profile", ""))
    if profile != "spherical":
        raise RuntimeError(
            "The generic radial text decorator now owns only spherical text; ovoid text must use the dedicated ovoid adapter."
        )

    height = float(route["height_mm"])
    rx_at, ry_at = _profile_functions(route)
    minimum_feature = float(program.manufacturing.minimum_feature_mm)
    first_feature, _ = entries[0]
    multiline = len(entries) > 1

    if multiline:
        shared_size, _block_center_z, line_z = _multiline_block_metrics(
            entries,
            route=route,
            minimum_feature=minimum_feature,
        )
    else:
        shared_size = 0.0
        line_z = ()

    pristine = shape
    base_volume = float(shape.Volume())
    current = shape
    expected_glyph_count = sum(
        1 for _feature, literal in entries for glyph in str(literal) if not glyph.isspace()
    )
    applied_glyph_count = 0
    band_cache: dict[tuple[str, float], tuple[cq.Shape, cq.Shape, float]] = {}

    for index, (feature, literal) in enumerate(entries):
        if multiline:
            z = float(line_z[index])
            requested_size = shared_size
        else:
            z = float(feature.anchor.vertical) * height
            requested_size = max(minimum_feature, float(feature.size.height_ratio) * height)
            half_size = 0.55 * min(requested_size, _SPHERICAL_MAX_TEXT_MM)
            safe_edge = max(half_size, 0.14 * height)
            z = min(height - safe_edge, max(safe_edge, z))

        t = min(1.0, max(0.0, z / height))
        local_rx = float(rx_at(t))
        local_ry = float(ry_at(t))
        effective_radius = math.sqrt(max(1e-9, local_rx * local_ry))

        if multiline and str(first_feature.anchor.region) == "front":
            u_offset = 0.0
        else:
            horizontal = float(first_feature.anchor.horizontal if multiline else feature.anchor.horizontal)
            u_offset = 0.25 * horizontal * (2.0 * math.pi * effective_radius)

        mode = "deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss"
        requested_depth = max(0.1, float(feature.size.depth_mm))
        cache_key = (mode, round(requested_depth, 6))
        if cache_key not in band_cache:
            band_cache[cache_key] = _surface_band_parts(
                pristine,
                requested_depth=requested_depth,
                mode=mode,
            )

        current, line_glyphs = _apply_spherical_line(
            current,
            pristine=pristine,
            route=route,
            text_value=str(literal),
            size=requested_size,
            mode=mode,
            z=z,
            u_offset=u_offset,
            surface_band_parts=band_cache[cache_key],
        )
        applied_glyph_count += line_glyphs

    final = current.clean()
    if not final.isValid() or len(tuple(final.Solids())) != 1:
        raise RuntimeError("Native spherical text did not preserve one valid CAD vessel solid.")
    if expected_glyph_count <= 0 or applied_glyph_count != expected_glyph_count:
        raise RuntimeError(
            "Native spherical text glyph integrity failed: "
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
    """Apply text to the promoted analytic spherical CAD body."""
    if not uses_native_radial_text(program):
        return mesh_result

    profile = _radial_profile(program)
    if profile != "spherical":
        raise RuntimeError(
            "Radial text fallback reached a non-spherical profile; the dedicated ovoid adapter should have handled it first."
        )

    route = motor.get("_analytic_radial")
    base_route = str(motor.get("_capability_route", ""))
    if not isinstance(route, dict) or base_route != _SPHERICAL_BASE_ROUTE:
        raise RuntimeError(
            "Spherical text requires the promoted analytic spherical body route; legacy volumetric fallback is not accepted."
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
    mesh, export_tolerance, export_angular_tolerance = _export_connected_spherical_text(
        final_shape,
        stl_path,
    )
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
    stage_seconds["native_spherical_cad_text"] = elapsed

    motor["_base_capability_route"] = _SPHERICAL_BASE_ROUTE
    motor["_capability_route"] = _SPHERICAL_TEXT_ROUTE
    motor["_native_radial_text"] = {
        "adapter_version": NATIVE_RADIAL_TEXT_ADAPTER_VERSION,
        "profile": "spherical",
        "method": "surface_band_clipped_tangent_glyphs",
        "layout": "coherent_multiline_block" if line_count > 1 else "single_line",
        "font": _SPHERICAL_FONT,
        "font_kind": _SPHERICAL_FONT_KIND,
        "line_count": line_count,
        "expected_glyph_count": expected_glyph_count,
        "applied_glyph_count": applied_glyph_count,
        "base_volume_mm3": base_volume,
        "final_volume_mm3": final_volume,
        "volume_delta_mm3": final_volume - base_volume,
        "export_tolerance_mm": export_tolerance,
        "export_angular_tolerance": export_angular_tolerance,
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