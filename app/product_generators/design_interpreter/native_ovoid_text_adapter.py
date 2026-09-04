from __future__ import annotations

"""Robust native text for the approved smooth ovoid CAD body.

The ovoid is a Y-scaled smooth revolution, so CadQuery projected-face offsets
can become null or tangent on its BSpline skin. This adapter keeps the exact
approved ovoid body and places each glyph in its local tangent frame. Every
emboss glyph straddles the wall slightly before fusing; every deboss glyph
straddles the wall before cutting. No voxel or implicit fallback is allowed.
"""

from dataclasses import replace
import math
from pathlib import Path
from time import perf_counter
from typing import Any

import cadquery as cq
import numpy as np

from .native_radial_cad_adapter import (
    _build_radial_shape,
    _load_welded_stl,
    _profile_functions,
)
from .native_radial_text_adapter import (
    _radial_line_contract,
    _radial_profile,
    _single_tessellated_component,
    uses_native_radial_text,
)
from .semantic_contract import DesignSemanticProgram


NATIVE_OVOID_TEXT_ADAPTER_VERSION = "NOVT.1-local-tangent-glyphs"
_OVOID_BASE_ROUTE = "analytic_cad_ovoid_primitive"
_OVOID_TEXT_ROUTE = "analytic_cad_ovoid_text"


def uses_native_ovoid_text(program: DesignSemanticProgram) -> bool:
    return uses_native_radial_text(program) and _radial_profile(program) == "ovoid"


def _numeric_derivative(function, value: float, *, step: float = 1e-4) -> float:
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


def _safe_line_size(radius: float, text_value: str, requested: float) -> float:
    glyph_count = max(1, len(text_value.strip()))
    usable_arc = math.pi * float(radius) * 0.72
    estimated_per_size = max(1.0, glyph_count * 0.72) * 1.18
    return min(float(requested), usable_arc / estimated_per_size)


def _glyph_tools(
    *,
    route: dict[str, Any],
    text_value: str,
    size: float,
    depth: float,
    mode: str,
    z: float,
    u_offset: float,
) -> tuple[cq.Shape, ...]:
    height = float(route["height_mm"])
    width = float(route["width_mm"])
    depth_y = float(route["depth_mm"])
    aspect_y = depth_y / width
    rx_at, _ = _profile_functions(route)

    t = min(1.0, max(0.0, float(z) / height))
    rx = float(rx_at(t))
    ry = rx * aspect_y
    actual_size = _safe_line_size(rx, text_value, size)
    drx_dz = _numeric_derivative(rx_at, t) / height
    dry_dz = drx_dz * aspect_y

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

    center_theta = -0.5 * math.pi + float(u_offset) / max(rx, 1e-6)
    # 0.8 mm was established experimentally as enough overlap for the approved
    # 106–112 mm ovoid while remaining far below the 4 mm nominal wall.
    anchor = min(0.80, max(0.35, 0.65 * float(depth)))
    tools: list[cq.Shape] = []

    for glyph, arc_center in zip(text_value, centers):
        if glyph.isspace():
            continue
        theta = center_theta + float(arc_center) / max(rx, 1e-6)
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
            thickness = float(depth) + anchor
        elif mode == "deboss":
            origin = point + normal * anchor
            thickness = -(float(depth) + anchor)
        else:
            raise ValueError(f"Unsupported ovoid text mode: {mode!r}")

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
            raise RuntimeError(f"Ovoid native glyph construction failed for {glyph!r}.") from error
        glyph_shapes = [value for value in values if isinstance(value, cq.Shape)]
        if not glyph_shapes:
            raise RuntimeError(f"Ovoid native glyph {glyph!r} produced no CAD tool.")
        tools.extend(glyph_shapes)

    if not tools:
        raise RuntimeError("Ovoid native text produced no glyph tools.")
    return tuple(tools)


def _apply_line(
    base: cq.Shape,
    *,
    route: dict[str, Any],
    text_value: str,
    size: float,
    depth: float,
    mode: str,
    z: float,
    u_offset: float,
) -> cq.Shape:
    tools = _glyph_tools(
        route=route,
        text_value=text_value,
        size=size,
        depth=depth,
        mode=mode,
        z=z,
        u_offset=u_offset,
    )
    current = base
    for index, tool in enumerate(tools):
        before = float(current.Volume())
        try:
            raw = (
                current.fuse(tool, tol=0.01)
                if mode == "emboss"
                else current.cut(tool, tol=0.01)
            ).clean()
        except Exception as error:
            raise RuntimeError(f"Ovoid native {mode} Boolean failed at glyph {index}.") from error
        solids = tuple(raw.Solids())
        if len(solids) != 1:
            raise RuntimeError(
                f"Ovoid native {mode} glyph {index} produced {len(solids)} CAD solids."
            )
        current = solids[0].clean()
        after = float(current.Volume())
        delta = after - before if mode == "emboss" else before - after
        if delta <= 1e-7:
            raise RuntimeError(
                f"Ovoid native {mode} glyph {index} produced no measurable relief."
            )
    return current


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
            size = slot_height
        else:
            z = float(feature.anchor.vertical) * height
            size = max(minimum_feature, float(feature.size.height_ratio) * height)

        half_size = 0.55 * size
        safe_edge = max(half_size, 0.14 * height)
        z = min(height - safe_edge, max(safe_edge, z))
        t = min(1.0, max(0.0, z / height))
        local_rx = float(rx_at(t))
        local_ry = local_rx * aspect_y
        effective_radius = math.sqrt(max(1e-9, local_rx * local_ry))
        if multiline and str(first_feature.anchor.region) == "front":
            u_offset = 0.0
        else:
            horizontal = float(
                first_feature.anchor.horizontal if multiline else feature.anchor.horizontal
            )
            u_offset = 0.25 * horizontal * (2.0 * math.pi * effective_radius)

        mode = "deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss"
        current = _apply_line(
            current,
            route=route,
            text_value=str(literal),
            size=size,
            depth=max(0.1, float(feature.size.depth_mm)),
            mode=mode,
            z=z,
            u_offset=u_offset,
        )

    final = current.clean()
    if not final.isValid() or len(tuple(final.Solids())) != 1:
        raise RuntimeError("Ovoid native text did not preserve one valid CAD vessel solid.")
    return final, base_volume, float(final.Volume()), len(entries)


def decorate_ovoid_mesh_result_with_native_text(
    mesh_result,
    motor: dict[str, Any],
    program: DesignSemanticProgram,
):
    if not uses_native_ovoid_text(program):
        return mesh_result
    route = motor.get("_analytic_radial")
    if (
        not isinstance(route, dict)
        or route.get("profile") != "ovoid"
        or motor.get("_capability_route") != _OVOID_BASE_ROUTE
    ):
        raise RuntimeError(
            "Ovoid native text requires the promoted analytic ovoid body route; "
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
    mesh = _single_tessellated_component(_load_welded_stl(stl_path))
    mesh.export(str(stl_path))
    components = tuple(mesh.split(only_watertight=False))

    checks = dict(getattr(mesh_result, "semantic_checks", {}) or {})
    checks["native_radial_text_volume_changed"] = abs(final_volume - base_volume) > 1e-7
    checks["native_radial_text_one_component"] = len(components) == 1
    checks["native_radial_text_mesh_compact"] = 0 < int(len(mesh.vertices)) < 100_000

    elapsed = perf_counter() - started
    stages = dict(getattr(mesh_result, "stage_seconds", {}) or {})
    stages["native_ovoid_cad_text"] = elapsed

    motor["_base_capability_route"] = _OVOID_BASE_ROUTE
    motor["_capability_route"] = _OVOID_TEXT_ROUTE
    motor["_native_radial_text"] = {
        "adapter_version": NATIVE_OVOID_TEXT_ADAPTER_VERSION,
        "profile": "ovoid",
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
        stage_seconds=stages,
        generation_seconds=float(mesh_result.generation_seconds) + elapsed,
    )
    decorated.validate()
    return decorated
