from __future__ import annotations

"""Native text reconnection for promoted spherical and ovoid DOBO planters.

Sphere and ovoid bodies stay on their smooth analytic CAD routes when semantic
text is requested. Text is removed from the volumetric hierarchy before body
generation, then projected directly onto the proven revolved CAD surface. This
prevents the legacy implicit/voxel fallback from deforming the body or creating
six-figure meshes.
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


NATIVE_RADIAL_TEXT_ADAPTER_VERSION = "NRT.1-revolved-surface-text"
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
    except (ValueError, RuntimeError) as first_error:
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
    try:
        if mode == "emboss":
            outward_depth = min(float(depth), 1.50)
            anchor_depth = min(0.16, max(0.06, 0.10 * outward_depth))
            primary = offset(projected, float(sign) * outward_depth, cap=True)
            anchor = offset(projected, -float(sign) * anchor_depth, cap=True)
            tool = primary.fuse(anchor, tol=0.01).clean()
        else:
            tool = offset(projected, float(sign) * float(depth), cap=True).clean()
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


def _apply_text_block(
    shape: cq.Shape,
    route: dict[str, Any],
    program: DesignSemanticProgram,
) -> tuple[cq.Shape, float, float, int]:
    entries = tuple(_radial_line_contract(program))
    if not entries:
        volume = float(shape.Volume())
        return shape, volume, volume, 0

    height = float(route["height_mm"])
    width = float(route["width_mm"])
    depth_y = float(route["depth_mm"])
    aspect_y = depth_y / width
    rx_at, _ = _profile_functions(route)
    minimum_feature = float(program.manufacturing.minimum_feature_mm)

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
        ry = rx * aspect_y
        effective_radius = math.sqrt(max(1e-9, rx * ry))
        if multiline and str(first_feature.anchor.region) == "front":
            u_offset = 0.0
        else:
            horizontal = float(
                first_feature.anchor.horizontal if multiline else feature.anchor.horizontal
            )
            u_offset = 0.25 * horizontal * (2.0 * math.pi * effective_radius)

        projected = _project_line(
            shape=current,
            rx=rx,
            ry=ry,
            z=z,
            text_value=str(literal),
            size=requested_size,
            u_offset=u_offset,
        )
        mode = "deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss"
        current = _apply_relief(
            current,
            projected,
            depth=max(0.1, float(feature.size.depth_mm)),
            mode=mode,
        )

    final = current.clean()
    if not final.isValid() or len(tuple(final.Solids())) != 1:
        raise RuntimeError("Native radial text did not preserve one valid CAD vessel solid.")
    return final, base_volume, float(final.Volume()), len(entries)


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
    final_shape, base_volume, final_volume, line_count = _apply_text_block(
        shape,
        route,
        program,
    )

    stl_path = Path(str(mesh_result.stl_path))
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(final_shape, str(stl_path), tolerance=0.08, angularTolerance=0.08)
    mesh = _load_welded_stl(stl_path)
    components = tuple(mesh.split(only_watertight=False))

    checks = dict(getattr(mesh_result, "semantic_checks", {}) or {})
    checks["native_radial_text_volume_changed"] = abs(final_volume - base_volume) > 1e-7
    checks["native_radial_text_one_component"] = len(components) == 1
    checks["native_radial_text_mesh_compact"] = 0 < int(len(mesh.vertices)) < 100_000

    elapsed = perf_counter() - started
    stage_seconds = dict(getattr(mesh_result, "stage_seconds", {}) or {})
    stage_seconds["native_radial_cad_text"] = elapsed

    motor["_base_capability_route"] = expected_base
    motor["_capability_route"] = final_route
    motor["_native_radial_text"] = {
        "adapter_version": NATIVE_RADIAL_TEXT_ADAPTER_VERSION,
        "profile": profile,
        "line_count": line_count,
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
