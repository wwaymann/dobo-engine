from __future__ import annotations

"""Native text reconnection for analytic tapered DOBO planters.

A tapered body must stay on the promoted CadQuery loft route when semantic text
is requested. Text is removed from the volumetric hierarchy before generation,
then DOBO's existing ConeSurfaceMapper + NativeSurfaceTextBuilder are applied to
the exact analytic body. This keeps cone shape, cavity and drain independent of
surface decoration.

The native tapered route also owns final text-to-surface placement. Generic
volumetric hierarchy diagnostics that belong only to those text nodes must not
block the proposal before the native mapper gets a chance to place them.
"""

from dataclasses import replace
import math
from pathlib import Path
import re
from time import perf_counter
from typing import Any
import unicodedata

import cadquery as cq
import numpy as np

from engine.body import build_body
from engine.context import EngineContext
from engine.drain import build_drain
from product_generators.surface_designer.native_text import NativeSurfaceTextBuilder
from product_generators.surface_mapping.cone_mapper import ConeSurfaceMapper

from .native_text_pipeline_adapter import (
    _line_contract,
    _load_welded_stl,
    _plumbing_feature,
    _text_features,
)
from .proposal_repair import ProposalValidationSnapshot, SemanticProposalRepairer
from .semantic_contract import DesignSemanticProgram


NATIVE_TAPERED_TEXT_ADAPTER_VERSION = "NTT.3-native-repair-boundary"
_TAPERED_TEXT_ROUTE = "analytic_cad_tapered_text"
_BASE_TAPERED_ROUTE = "analytic_cad_tapered_primitive"


def uses_native_tapered_text(program: DesignSemanticProgram) -> bool:
    """Return true only for simple tapered vessels whose decoration is text."""
    if program.body.family != "tapered" or not _text_features(program):
        return False
    unsupported = tuple(
        feature
        for feature in program.features
        if feature.form_hint != "text" and not _plumbing_feature(feature)
    )
    return not unsupported


def _failure_owned_by_native_text(name: str, text_ids: set[str]) -> bool:
    """Identify generic hierarchy diagnostics that belong to native text nodes."""
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


def install_native_tapered_text_repair_boundary() -> None:
    """Exclude native text nodes from the generic volumetric repair boundary.

    SemanticProposalRepairer evaluates hierarchy placements before the
    structural pipeline strips text from that hierarchy. For tapered native text
    this can create false failures such as ``root/feature_text_walter...`` even
    though the final placement is owned by ConeSurfaceMapper. Filter only the
    diagnostics that belong to text nodes and only when the whole program is
    eligible for the native tapered-text route. Non-text geometry is untouched.
    """
    current = SemanticProposalRepairer._evaluate.__func__
    if getattr(current, "_dobo_native_tapered_text_repair_boundary", False):
        return
    previous = current

    def _evaluate_with_native_tapered_text(cls, program: DesignSemanticProgram):
        snapshot, compilation = previous(cls, program)
        if not uses_native_tapered_text(program):
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

    _evaluate_with_native_tapered_text._dobo_native_tapered_text_repair_boundary = True
    SemanticProposalRepairer._evaluate = classmethod(_evaluate_with_native_tapered_text)


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _tapered_line_contract(program: DesignSemanticProgram):
    """Reuse canonical line parsing and accept the Lab's A / B / C phrasing."""
    entries = tuple(_line_contract(program))
    if len(entries) > 1:
        return entries

    prompt = str(getattr(program.source, "prompt", "") or "")
    normalized = _plain(prompt)
    if "/" not in prompt or "linea" not in normalized:
        return entries

    # Typical user phrasing: "exactamente en tres líneas: PLANTA / UNA / IDEA."
    marker = re.search(r"lineas?\s*:\s*", normalized)
    if marker is None:
        return entries
    raw_start = marker.end()
    # Accent removal does not change string length for the characters used here,
    # so the same offset selects the payload in the original prompt.
    payload = prompt[raw_start:]
    payload = re.split(r"[.\n\r]", payload, maxsplit=1)[0]
    parts = tuple(
        part.strip(" \t,;:\"'“”")
        for part in payload.split("/")
        if part.strip(" \t,;:\"'“”")
    )
    if not 2 <= len(parts) <= 6:
        return entries
    text_features = _text_features(program)
    if not text_features:
        return entries
    feature = text_features[0]
    return tuple((feature, part.upper()) for part in parts)


def _base_shape(route: dict[str, Any]) -> cq.Shape:
    context = EngineContext({
        "top_diameter": float(route["top_diameter_mm"]),
        "bottom_diameter": float(route["bottom_diameter_mm"]),
        "height": float(route["height_mm"]),
        "wall_thickness": float(route["wall_mm"]),
        "bottom_thickness": float(route["bottom_mm"]),
        "drain_hole": bool(route["drain_required"]),
        "drain_diameter": float(route["drain_diameter_mm"]),
    })
    body = build_body(None, context)
    body = build_drain(body, context)
    shape = body.val().clean()
    if not isinstance(shape, cq.Shape) or not shape.isValid():
        raise RuntimeError("Native tapered text could not reconstruct the analytic CAD body.")
    if len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Native tapered text base must contain exactly one CAD solid.")
    return shape


def _apply_text_block(
    shape: cq.Shape,
    route: dict[str, Any],
    program: DesignSemanticProgram,
) -> tuple[cq.Shape, float, float, int]:
    entries = tuple(_tapered_line_contract(program))
    if not entries:
        volume = float(shape.Volume())
        return shape, volume, volume, 0

    height = float(route["height_mm"])
    base_radius = 0.5 * float(route["bottom_diameter_mm"])
    top_radius = 0.5 * float(route["top_diameter_mm"])
    minimum_feature = float(program.manufacturing.minimum_feature_mm)
    surface = ConeSurfaceMapper(
        base_radius=base_radius,
        top_radius=top_radius,
        height=height,
    )
    builder = NativeSurfaceTextBuilder()

    first_feature, _ = entries[0]
    multiline = len(entries) > 1
    gap_ratio = 0.22
    slot_height = max(
        minimum_feature,
        float(first_feature.size.height_ratio) * height,
    )
    gap = gap_ratio * slot_height if multiline else 0.0
    total_block_height = (
        len(entries) * slot_height
        + max(len(entries) - 1, 0) * gap
    )
    if multiline and str(first_feature.anchor.region) == "front":
        block_center = 0.5 * height
    else:
        block_center = float(first_feature.anchor.vertical) * height
    block_top = block_center + 0.5 * total_block_height

    base_volume = float(shape.Volume())
    current = shape
    for index, (feature, literal) in enumerate(entries):
        if multiline:
            v_offset = block_top - 0.5 * slot_height - index * (slot_height + gap)
            size = slot_height
        else:
            v_offset = float(feature.anchor.vertical) * height
            size = max(minimum_feature, float(feature.size.height_ratio) * height)

        # Keep enough room from the bottom and rim for the whole glyph contour.
        half_size = 0.55 * size
        safe_edge = max(half_size, 0.12 * height)
        v_offset = min(height - safe_edge, max(safe_edge, v_offset))
        local_radius = float(surface.radius_at(v_offset))

        if multiline and str(first_feature.anchor.region) == "front":
            u_offset = 0.0
        else:
            horizontal = float(
                first_feature.anchor.horizontal if multiline else feature.anchor.horizontal
            )
            u_offset = 0.25 * horizontal * (2.0 * math.pi * local_radius)

        result = builder.apply(
            base_shape=current,
            surface=surface,
            text_value=str(literal),
            size=size,
            depth=max(0.1, float(feature.size.depth_mm)),
            mode="deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss",
            font="DejaVu Sans",
            kind="regular",
            u_offset=u_offset,
            v_offset=v_offset,
        )
        current = result.shape

    final = current.clean()
    if not final.isValid() or len(tuple(final.Solids())) != 1:
        raise RuntimeError("Native tapered text did not preserve one valid CAD vessel solid.")
    return final, base_volume, float(final.Volume()), len(entries)


def decorate_tapered_mesh_result_with_native_text(
    mesh_result,
    motor: dict[str, Any],
    program: DesignSemanticProgram,
):
    """Apply semantic text to the promoted tapered CAD body, never to voxel geometry."""
    if not uses_native_tapered_text(program):
        return mesh_result

    route = motor.get("_analytic_tapered")
    if not isinstance(route, dict) or motor.get("_capability_route") != _BASE_TAPERED_ROUTE:
        raise RuntimeError(
            "Tapered text requires the promoted analytic tapered body route; "
            "legacy volumetric fallback is not accepted."
        )

    started = perf_counter()
    shape = _base_shape(route)
    final_shape, base_volume, final_volume, line_count = _apply_text_block(shape, route, program)

    output = motor.get("output", {})
    stl_path = Path(str(mesh_result.stl_path))
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(final_shape, str(stl_path), tolerance=0.035, angularTolerance=0.08)
    mesh = _load_welded_stl(stl_path)
    components = tuple(mesh.split(only_watertight=False))

    checks = dict(getattr(mesh_result, "semantic_checks", {}) or {})
    checks["native_tapered_text_volume_changed"] = abs(final_volume - base_volume) > 1e-8
    checks["native_tapered_text_one_component"] = len(components) == 1

    elapsed = perf_counter() - started
    stage_seconds = dict(getattr(mesh_result, "stage_seconds", {}) or {})
    stage_seconds["native_tapered_cad_text"] = elapsed

    motor["_base_capability_route"] = _BASE_TAPERED_ROUTE
    motor["_capability_route"] = _TAPERED_TEXT_ROUTE
    motor["_native_tapered_text"] = {
        "adapter_version": NATIVE_TAPERED_TEXT_ADAPTER_VERSION,
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
        max_generation_seconds=max(
            float(getattr(mesh_result, "max_generation_seconds", 45.0)),
            float(output.get("max_generation_seconds", 45.0)),
        ),
    )
    decorated.validate()
    return decorated


install_native_tapered_text_repair_boundary()
