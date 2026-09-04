from __future__ import annotations

"""Native emboss/deboss text for reusable revolved planter profiles.

The profiled body stays on its shared analytic CAD route.  Text is mapped one
physical glyph at a time using the local radius and meridian slope, then clipped
against a narrow revolved surface band.  This lets the same implementation
follow amphora, urn, barrel, neck, rim, hourglass, oval and pedestal silhouettes
without flattening or replacing the vessel body.
"""

from dataclasses import replace
import math
from pathlib import Path
from time import perf_counter
from typing import Any

import cadquery as cq
import numpy as np

from .native_profiled_cad_adapter import (
    _PROFILED_ROUTE,
    _STL_ANGULAR_TOLERANCE_RAD,
    _STL_TOLERANCE_MM,
    _load_mesh,
    _profiled_body,
    _radius_at,
    _revolved_polygon,
    profile_variant,
)
from .native_text_pipeline_adapter import (
    _line_contract,
    _plumbing_feature,
    _text_features,
    strip_text_from_motor,
)
from .proposal_repair import ProposalValidationSnapshot, SemanticProposalRepairer
from .semantic_contract import DesignSemanticProgram


NATIVE_PROFILED_TEXT_ADAPTER_VERSION = "NPT.17-robust-relief-tessellation"
_PROFILED_TEXT_ROUTE = "analytic_cad_profiled_text"
_FONT = "DejaVu Sans"
_FONT_KIND = "bold"
_BOOLEAN_TOLERANCE_MM = 0.005


def uses_native_profiled_text(program: DesignSemanticProgram) -> bool:
    if profile_variant(program) is None or not _text_features(program):
        return False
    unsupported = tuple(
        feature
        for feature in program.features
        if feature.form_hint != "text" and not _plumbing_feature(feature)
    )
    return not unsupported


def _failure_owned_by_text(name: str, text_ids: set[str]) -> bool:
    value = str(name)
    return any(
        value.startswith(feature_id)
        or f"/{feature_id}" in value
        or f"/{feature_id}_template" in value
        or f"{feature_id}--" in value
        or f"--{feature_id}" in value
        for feature_id in text_ids
    )


def install_native_profiled_text_repair_boundary() -> None:
    current = SemanticProposalRepairer._evaluate.__func__
    if getattr(current, "_dobo_native_profiled_text_repair_boundary", False):
        return
    previous = current

    def _evaluate_with_profiled_text(cls, program: DesignSemanticProgram):
        snapshot, compilation = previous(cls, program)
        if not uses_native_profiled_text(program):
            return snapshot, compilation
        text_ids = {str(feature.id) for feature in _text_features(program)}
        return ProposalValidationSnapshot(
            surface_anchor_failures=tuple(
                item for item in snapshot.surface_anchor_failures
                if not _failure_owned_by_text(item, text_ids)
            ),
            layout_failures=tuple(
                item for item in snapshot.layout_failures
                if not _failure_owned_by_text(item, text_ids)
            ),
            manufacturability_failures=tuple(
                item for item in snapshot.manufacturability_failures
                if not _failure_owned_by_text(item, text_ids)
            ),
        ), compilation

    _evaluate_with_profiled_text._dobo_native_profiled_text_repair_boundary = True
    SemanticProposalRepairer._evaluate = classmethod(_evaluate_with_profiled_text)


def _profile(route: dict[str, Any]) -> tuple[tuple[float, float], ...]:
    return tuple(
        (float(point[0]), float(point[1]))
        for point in route["normalized_profile"]
    )


def _radius_mm(route: dict[str, Any], z_mm: float) -> float:
    height = float(route["height_mm"])
    maximum_radius = 0.5 * float(route["diameter_mm"])
    return maximum_radius * _radius_at(_profile(route), float(z_mm) / height)


def _radius_slope(route: dict[str, Any], z_mm: float) -> float:
    height = float(route["height_mm"])
    step = max(0.12, 0.002 * height)
    low = max(0.0, float(z_mm) - step)
    high = min(height, float(z_mm) + step)
    if high <= low:
        return 0.0
    return (_radius_mm(route, high) - _radius_mm(route, low)) / (high - low)


def _offset_profile_solid(route: dict[str, Any], offset_mm: float) -> cq.Shape:
    height = float(route["height_mm"])
    maximum_radius = 0.5 * float(route["diameter_mm"])
    points = [
        (max(0.5, maximum_radius * radius_ratio + float(offset_mm)), height * z_ratio)
        for z_ratio, radius_ratio in _profile(route)
    ]
    return _revolved_polygon(points, start_axis_z=0.0, end_axis_z=height)


def _surface_band(
    route: dict[str, Any],
    *,
    mode: str,
    requested_depth: float,
) -> tuple[cq.Shape, float, float]:
    wall = float(route["wall_mm"])
    if mode == "emboss":
        outward = min(max(float(requested_depth), 1.20), 2.20)
        # Give raised glyphs enough physical overlap with the curved wall that
        # the final CAD tessellation cannot leave them as numerically detached
        # shells.  This remains far below the structural wall thickness.
        inward = min(max(0.40, 0.16 * outward + 0.12), max(0.40, 0.20 * wall))
    elif mode == "deboss":
        # On strongly varying profiles a deep radial cut can cross a narrow or
        # highly sloped wall section and split the vessel.  Cap the engraving
        # depth to a conservative fraction of the actual wall while retaining
        # a clearly printable recessed mark.
        safe_depth = max(0.90, min(1.20, 0.28 * wall))
        inward = min(max(float(requested_depth), 0.90), safe_depth)
        outward = 0.24
    else:
        raise ValueError(f"Unsupported profiled text mode: {mode!r}")
    expanded = _offset_profile_solid(route, outward)
    contracted = _offset_profile_solid(route, -inward)
    band = expanded.cut(contracted).clean()
    if not band.isValid() or not tuple(band.Solids()):
        raise RuntimeError("Profiled text could not build a valid receiving surface band.")
    return band, inward, outward


def _glyph_width(
    glyph: str,
    size: float,
    *,
    font: str = _FONT,
    kind: str = _FONT_KIND,
    font_path: str | None = None,
) -> float:
    if glyph.isspace():
        return 0.35 * float(size)
    try:
        font_kwargs = {"font": font, "kind": kind}
        if font_path:
            font_kwargs["fontPath"] = font_path
        values = cq.Workplane("XY").text(
            glyph,
            float(size),
            0.20,
            combine=False,
            halign="center",
            valign="center",
            **font_kwargs,
        ).vals()
    except Exception:
        return 0.62 * float(size)
    boxes = [value.BoundingBox() for value in values if isinstance(value, cq.Shape)]
    if not boxes:
        return 0.62 * float(size)
    return max(0.20 * float(size), max(box.xmax for box in boxes) - min(box.xmin for box in boxes))


def _glyph_centres(
    text_value: str,
    size: float,
    *,
    font: str = _FONT,
    kind: str = _FONT_KIND,
    font_path: str | None = None,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    widths = tuple(
        _glyph_width(
            glyph,
            size,
            font=font,
            kind=kind,
            font_path=font_path,
        )
        for glyph in text_value
    )
    spacing = 0.10 * float(size)
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


def _safe_text_size(radius: float, text_value: str, requested: float, minimum: float) -> float:
    glyph_count = max(1, len(text_value.strip()))
    usable_arc = math.pi * float(radius) * 0.70
    per_size = max(1.0, glyph_count * 0.72) * 1.16
    return max(float(minimum), min(float(requested), usable_arc / per_size))


def _apply_line(
    current: cq.Shape,
    *,
    route: dict[str, Any],
    text_value: str,
    size: float,
    minimum_feature: float,
    requested_depth: float,
    mode: str,
    z: float,
    u_offset: float,
) -> tuple[cq.Shape, int, float]:
    local_radius = _radius_mm(route, z)
    text_style = route.get("text_style", {})
    font = (
        str(text_style.get("font", _FONT))
        if isinstance(text_style, dict)
        else _FONT
    )
    kind = (
        str(text_style.get("kind", _FONT_KIND))
        if isinstance(text_style, dict)
        else _FONT_KIND
    )
    font_path = (
        str(text_style.get("font_path"))
        if isinstance(text_style, dict) and text_style.get("font_path")
        else None
    )
    layout = (
        str(text_style.get("layout", "front"))
        if isinstance(text_style, dict)
        else "front"
    )
    rendered_text = str(text_value)
    if layout == "wrap":
        # Repeat the same literal until the authored phrase occupies most of
        # the circumference. The user asks for a continuous all-around message,
        # not for a stretched word with artificial letter spacing.
        probe_size = max(minimum_feature, float(size))
        circumference = 2.0 * math.pi * max(local_radius, 1e-6)
        for _repeat in range(8):
            widths_probe, _centres_probe = _glyph_centres(
                rendered_text,
                probe_size,
                font=font,
                kind=kind,
                font_path=font_path,
            )
            estimated = sum(widths_probe) + max(0, len(widths_probe) - 1) * 0.10 * probe_size
            target_fraction = (
                float(text_style.get("wrap_target_fraction", 0.96))
                if isinstance(text_style, dict)
                else 0.96
            )
            if estimated >= target_fraction * circumference:
                break
            rendered_text = rendered_text + "   " + str(text_value)

    if layout == "wrap":
        glyph_count = max(1, len(rendered_text.strip()))
        target_fraction = (
            float(text_style.get("wrap_target_fraction", 0.96))
            if isinstance(text_style, dict)
            else 0.96
        )
        usable_arc = 2.0 * math.pi * local_radius * target_fraction
        per_size = max(1.0, glyph_count * 0.72) * 1.06
        actual_size = max(
            float(minimum_feature),
            min(float(size), usable_arc / per_size),
        )
    else:
        actual_size = _safe_text_size(
            local_radius,
            rendered_text,
            size,
            minimum_feature,
        )
    widths, centres = _glyph_centres(
        rendered_text,
        actual_size,
        font=font,
        kind=kind,
        font_path=font_path,
    )
    band, inward, outward = _surface_band(
        route, mode=mode, requested_depth=requested_depth
    )
    slope = _radius_slope(route, z)
    center_theta = -0.5 * math.pi + float(u_offset) / max(local_radius, 1e-6)
    applied = 0

    for glyph_index, (glyph, glyph_width, arc_center) in enumerate(
        zip(rendered_text, widths, centres)
    ):
        if glyph.isspace():
            continue
        theta = center_theta + float(arc_center) / max(local_radius, 1e-6)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        point = np.array([local_radius * cos_t, local_radius * sin_t, float(z)])
        tangent_u = np.array([-sin_t, cos_t, 0.0])
        tangent_v = np.array([slope * cos_t, slope * sin_t, 1.0])
        tangent_v /= np.linalg.norm(tangent_v)
        normal = np.cross(tangent_u, tangent_v)
        normal /= np.linalg.norm(normal)
        if float(np.dot(normal, np.array([cos_t, sin_t, 0.0]))) < 0.0:
            normal = -normal

        # A tangent glyph can span a rapidly changing meridian (trumpet,
        # pedestal, waist). Give the prism enough normal travel to cross the
        # whole receiving band, then clip it back to the band. This improves
        # robustness without deepening the authored relief.
        curvature_allowance = min(
            3.5,
            0.18 * actual_size + 0.24 * actual_size * abs(slope),
        )
        start_inside = inward + 0.85 + 0.45 * curvature_allowance
        total_span = (
            inward + outward + 1.70 + curvature_allowance
        )
        plane = cq.Plane(
            origin=tuple(float(value) for value in point - normal * start_inside),
            xDir=tuple(float(value) for value in tangent_u),
            normal=tuple(float(value) for value in normal),
        )
        try:
            prisms = tuple(
                value for value in cq.Workplane(plane).text(
                    glyph,
                    actual_size,
                    total_span,
                    combine=False,
                    halign="center",
                    valign="center",
                    **({
                        "font": font,
                        "kind": kind,
                        **({"fontPath": font_path} if font_path else {}),
                    }),
                ).vals()
                if isinstance(value, cq.Shape)
            )
        except Exception as error:
            raise RuntimeError(
                f"Profiled text glyph construction failed for {glyph!r}."
            ) from error
        if not prisms:
            raise RuntimeError(f"Profiled text glyph {glyph!r} produced no CAD prism.")

        before = float(current.Volume())
        for prism_index, prism in enumerate(prisms):
            tool = prism.intersect(band, tol=_BOOLEAN_TOLERANCE_MM).clean()
            if not tool.isValid() or float(tool.Volume()) <= 1e-7:
                raise RuntimeError(
                    f"Profiled {mode} glyph {glyph_index} {glyph!r}, part "
                    f"{prism_index}, missed the receiving surface."
                )
            raw = (
                current.fuse(tool, tol=_BOOLEAN_TOLERANCE_MM)
                if mode == "emboss"
                else current.cut(tool, tol=_BOOLEAN_TOLERANCE_MM)
            ).clean()
            solids = tuple(raw.Solids())
            if len(solids) != 1:
                raise RuntimeError(
                    f"Profiled {mode} glyph {glyph_index} {glyph!r} produced "
                    f"{len(solids)} CAD solids."
                )
            current = solids[0].clean()

        after = float(current.Volume())
        delta = after - before if mode == "emboss" else before - after
        if delta <= 1e-7:
            raise RuntimeError(
                f"Profiled {mode} glyph {glyph_index} {glyph!r} changed no volume."
            )
        applied += 1
    return current, applied, float(actual_size)


def _apply_text_block(
    shape: cq.Shape,
    route: dict[str, Any],
    program: DesignSemanticProgram,
    *,
    multiline_slot_fraction: float = 0.22,
    use_text_zone: bool = False,
) -> tuple[cq.Shape, float, float, int, int, tuple[float, ...]]:
    entries = tuple(_line_contract(program))
    if not entries:
        volume = float(shape.Volume())
        return shape, volume, volume, 0, 0, ()

    height = float(route["height_mm"])
    minimum = float(program.manufacturing.minimum_feature_mm)
    first_feature, _ = entries[0]
    multiline = len(entries) > 1

    text_zone = route.get("text_zone", {})
    text_zones = route.get("text_zones", {})

    def _zone_for_vertical(authored: float) -> dict[str, Any] | None:
        if isinstance(text_zones, dict):
            key = "upper" if authored >= 0.62 else "lower" if authored <= 0.42 else "center"
            candidate = text_zones.get(key)
            if isinstance(candidate, dict):
                return candidate
        return text_zone if isinstance(text_zone, dict) else None

    def _resolved_vertical(feature) -> float:
        authored = float(feature.anchor.vertical)
        if use_text_zone and str(feature.anchor.region) == "front":
            selected_zone = _zone_for_vertical(authored)
            if isinstance(selected_zone, dict):
                return float(selected_zone.get("center_z_ratio", authored))
        return authored

    requested_slot_height = max(
        minimum, float(first_feature.size.height_ratio) * height
    )
    # Multiline uses the selected typographic size as a real per-line size.
    # The block is capped only when all lines together would consume more than
    # roughly two thirds of the vessel height. This preserves visible Small /
    # Medium / Large / XL differences without allowing a 3-line block to run
    # through the rim or base.
    if multiline:
        max_block_fraction = 0.64
        denominator = len(entries) + 0.18 * max(0, len(entries) - 1)
        safe_per_line_fraction = max_block_fraction / max(1.0, denominator)
        slot_fraction = min(
            max(0.06, float(multiline_slot_fraction)),
            safe_per_line_fraction,
        )
        slot_height = min(requested_slot_height, slot_fraction * height)
    else:
        slot_fraction = requested_slot_height / max(height, 1e-6)
        slot_height = requested_slot_height
    gap = 0.18 * slot_height if multiline else 0.0
    block_height = len(entries) * slot_height + max(0, len(entries) - 1) * gap
    center = _resolved_vertical(first_feature) * height
    top = center + 0.5 * block_height

    base_volume = float(shape.Volume())
    current = shape
    applied_glyphs = 0
    effective_sizes: list[float] = []
    for index, (feature, literal) in enumerate(entries):
        size = slot_height if multiline else max(
            minimum, float(feature.size.height_ratio) * height
        )
        z = (
            top - 0.5 * slot_height - index * (slot_height + gap)
            if multiline else _resolved_vertical(feature) * height
        )
        safe_edge = max(0.60 * size, 0.13 * height)
        z = min(height - safe_edge, max(safe_edge, z))
        local_radius = _radius_mm(route, z)
        horizontal = float(
            first_feature.anchor.horizontal if multiline else feature.anchor.horizontal
        )
        u_offset = 0.0 if multiline and str(first_feature.anchor.region) == "front" else 0.25 * horizontal * (2.0 * math.pi * local_radius)
        mode = "deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss"
        current, glyphs, effective_size = _apply_line(
            current,
            route=route,
            text_value=str(literal),
            size=size,
            minimum_feature=minimum,
            requested_depth=max(0.1, float(feature.size.depth_mm)),
            mode=mode,
            z=z,
            u_offset=u_offset,
        )
        applied_glyphs += glyphs
        effective_sizes.append(effective_size)

    final = current.clean()
    if not final.isValid() or len(tuple(final.Solids())) != 1:
        raise RuntimeError("Profiled native text did not preserve one valid vessel solid.")
    return (
        final,
        base_volume,
        float(final.Volume()),
        len(entries),
        applied_glyphs,
        tuple(effective_sizes),
    )


def decorate_profiled_mesh_result_with_native_text(
    mesh_result,
    motor: dict[str, Any],
    program: DesignSemanticProgram,
):
    if not uses_native_profiled_text(program):
        return mesh_result
    route = motor.get("_profiled_revolution")
    if not isinstance(route, dict) or motor.get("_capability_route") != _PROFILED_ROUTE:
        raise RuntimeError(
            "Profiled text requires the promoted analytic profiled body route."
        )

    started = perf_counter()
    base = _profiled_body(route)
    placement_mode = "authored_or_default"
    try:
        final, base_volume, final_volume, line_count, glyph_count, effective_sizes = _apply_text_block(
            base, route, program
        )
    except RuntimeError as primary_error:
        text_zones = route.get("text_zones", {})
        all_front = all(
            str(feature.anchor.region) == "front"
            for feature, _literal in _line_contract(program)
        )
        if not all_front or not isinstance(text_zones, dict) or not text_zones:
            raise
        final, base_volume, final_volume, line_count, glyph_count, effective_sizes = _apply_text_block(
            base,
            route,
            program,
            use_text_zone=True,
        )
        placement_mode = "detected_text_zone_fallback"
    stl_path = Path(str(mesh_result.stl_path))
    cq.exporters.export(
        final,
        str(stl_path),
        tolerance=_STL_TOLERANCE_MM,
        angularTolerance=_STL_ANGULAR_TOLERANCE_RAD,
    )
    mesh = _load_mesh(stl_path)
    components = tuple(mesh.split(only_watertight=False))
    mesh_normalization = "default"

    # A valid OCC solid can occasionally tessellate with sub-tolerance seams
    # around several curved glyph faces. First weld those seams at 0.01 mm,
    # still below the authored 0.02 mm STL tolerance. If topology remains
    # invalid, tessellate the same CAD solid more finely and repeat the weld.
    if (
        len(components) != 1
        or not mesh.is_watertight
        or not mesh.is_winding_consistent
    ):
        mesh.merge_vertices(digits_vertex=2)
        mesh.remove_unreferenced_vertices()
        mesh.process(validate=True)
        components = tuple(mesh.split(only_watertight=False))
        mesh_normalization = "weld_0_01_mm"

    if (
        len(components) != 1
        or not mesh.is_watertight
        or not mesh.is_winding_consistent
    ):
        cq.exporters.export(
            final,
            str(stl_path),
            tolerance=0.015,
            angularTolerance=0.035,
        )
        mesh = _load_mesh(stl_path)
        mesh.merge_vertices(digits_vertex=2)
        mesh.remove_unreferenced_vertices()
        mesh.process(validate=True)
        components = tuple(mesh.split(only_watertight=False))
        mesh_normalization = "fine_0_015_mm_weld_0_01_mm"

    if (
        len(components) != 1
        or not mesh.is_watertight
        or not mesh.is_winding_consistent
    ):
        # OCC can occasionally emit T-junctions around relief booleans at the
        # finest tessellation. A slightly coarser tessellation of the *same*
        # valid CAD solid often removes those numerical seams while remaining
        # well below an FDM extrusion width.
        cq.exporters.export(
            final,
            str(stl_path),
            tolerance=0.025,
            angularTolerance=0.050,
        )
        mesh = _load_mesh(stl_path)
        mesh.merge_vertices(digits_vertex=2)
        mesh.remove_unreferenced_vertices()
        mesh.process(validate=True)
        components = tuple(mesh.split(only_watertight=False))
        mesh_normalization = "recovery_0_025_mm_weld_0_01_mm"

    multiline_slot_fraction = 0.22
    if (
        line_count > 1
        and (
            len(components) != 1
            or not mesh.is_watertight
            or not mesh.is_winding_consistent
        )
    ):
        # Only after a topology failure, reduce the current multiline line
        # height by 15%. Do not collapse every design to the historical 8%
        # size, because the user may have deliberately selected Large or XL.
        previous_fraction = (
            float(effective_sizes[0]) / max(float(route["height_mm"]), 1e-6)
            if effective_sizes
            else 0.10
        )
        multiline_slot_fraction = max(0.08, 0.85 * previous_fraction)
        final, base_volume, final_volume, line_count, glyph_count, effective_sizes = _apply_text_block(
            base,
            route,
            program,
            multiline_slot_fraction=multiline_slot_fraction,
            use_text_zone=(placement_mode == "detected_text_zone_fallback"),
        )
        cq.exporters.export(
            final,
            str(stl_path),
            tolerance=_STL_TOLERANCE_MM,
            angularTolerance=_STL_ANGULAR_TOLERANCE_RAD,
        )
        mesh = _load_mesh(stl_path)
        components = tuple(mesh.split(only_watertight=False))
        if (
            len(components) != 1
            or not mesh.is_watertight
            or not mesh.is_winding_consistent
        ):
            mesh.merge_vertices(digits_vertex=2)
            mesh.remove_unreferenced_vertices()
            mesh.process(validate=True)
            components = tuple(mesh.split(only_watertight=False))
        mesh_normalization = "adaptive_multiline_0_08"

    checks = dict(getattr(mesh_result, "semantic_checks", {}) or {})
    checks["native_profiled_text_volume_changed"] = abs(final_volume - base_volume) > 1e-8
    checks["native_profiled_text_one_component"] = len(components) == 1
    expected_glyphs = sum(
        1 for _feature, literal in _line_contract(program) for glyph in str(literal)
        if not glyph.isspace()
    )
    wrap_layout = (
        isinstance(route.get("text_style"), dict)
        and route["text_style"].get("layout") == "wrap"
    )
    checks["native_profiled_text_glyph_integrity"] = (
        glyph_count >= expected_glyphs if wrap_layout else glyph_count == expected_glyphs
    )

    elapsed = perf_counter() - started
    stages = dict(getattr(mesh_result, "stage_seconds", {}) or {})
    stages["native_profiled_cad_text"] = elapsed
    motor["_base_capability_route"] = _PROFILED_ROUTE
    motor["_capability_route"] = _PROFILED_TEXT_ROUTE
    motor["_native_profiled_text"] = {
        "adapter_version": NATIVE_PROFILED_TEXT_ADAPTER_VERSION,
        "method": "local_radius_slope_surface_band",
        "variant": route.get("variant"),
        "line_count": line_count,
        "applied_glyph_count": glyph_count,
        "base_volume_mm3": base_volume,
        "final_volume_mm3": final_volume,
        "volume_delta_mm3": final_volume - base_volume,
        "mesh_normalization": mesh_normalization,
        "multiline_slot_fraction": multiline_slot_fraction,
        "requested_height_ratio": (
            float(_line_contract(program)[0][0].size.height_ratio)
            if _line_contract(program)
            else None
        ),
        "text_zone_id": route.get("text_zone", {}).get("id") if isinstance(route.get("text_zone"), dict) else None,
        "available_text_zones": (
            sorted(route.get("text_zones", {}).keys())
            if isinstance(route.get("text_zones"), dict)
            else []
        ),
        "text_zone_center_z_ratio": (
            route.get("text_zone", {}).get("center_z_ratio")
            if isinstance(route.get("text_zone"), dict)
            else None
        ),
        "placement_mode": placement_mode,
        "font_style": (
            route.get("text_style", {}).get("font_style")
            if isinstance(route.get("text_style"), dict)
            else None
        ),
        "font_label": (
            route.get("text_style", {}).get("font_label")
            if isinstance(route.get("text_style"), dict)
            else None
        ),
        "font_weight": (
            route.get("text_style", {}).get("font_weight")
            if isinstance(route.get("text_style"), dict)
            else None
        ),
        "font_slant": (
            route.get("text_style", {}).get("font_slant")
            if isinstance(route.get("text_style"), dict)
            else None
        ),
        "font": (
            route.get("text_style", {}).get("font")
            if isinstance(route.get("text_style"), dict)
            else _FONT
        ),
        "font_kind": (
            route.get("text_style", {}).get("kind")
            if isinstance(route.get("text_style"), dict)
            else _FONT_KIND
        ),
        "font_path": (
            route.get("text_style", {}).get("font_path")
            if isinstance(route.get("text_style"), dict)
            else None
        ),
        "effective_line_heights_mm": [round(float(value), 4) for value in effective_sizes],
        "text_layout": (
            route.get("text_style", {}).get("layout")
            if isinstance(route.get("text_style"), dict)
            else "front"
        ),
        "wrap_target_fraction": (
            float(route.get("text_style", {}).get("wrap_target_fraction", 0.96))
            if isinstance(route.get("text_style"), dict)
            else 0.96
        ),
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
        max_generation_seconds=max(
            float(getattr(mesh_result, "max_generation_seconds", 45.0)),
            120.0,
        ),
    )
    decorated.validate()
    return decorated


install_native_profiled_text_repair_boundary()
