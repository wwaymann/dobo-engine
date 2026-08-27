from __future__ import annotations

"""Adapter that reconnects DOBO's existing native CAD text capability.

This is intentionally an orchestration layer, not another text engine.
The structural engine owns the vessel/body. Cylindrical text is removed from
voxel generation, then the already-existing SurfaceDesigner native text tool is
mapped on an analytic reference cylinder and booleaned onto the generated body.
"""

from dataclasses import replace
from pathlib import Path
from typing import Any

import cadquery as cq
import numpy as np
import trimesh

from .semantic_contract import DesignSemanticProgram
from . import core_capability_reconnection as _text_core
from .text_surface_consolidation import _prompt_lines
from product_generators.surface_designer.advanced_body_adapter import (
    load_advanced_stl_as_cadquery_shape,
)
from product_generators.surface_designer.native_text import NativeSurfaceTextBuilder
from product_generators.surface_mapping.cylinder_mapper import CylinderSurfaceMapper


NATIVE_TEXT_PIPELINE_ADAPTER_VERSION = "NTC.1-existing-native-cad-reconnection"


def _text_features(program: DesignSemanticProgram):
    return tuple(feature for feature in program.features if feature.form_hint == "text")


def body_program_without_text(program: DesignSemanticProgram) -> DesignSemanticProgram:
    """Return a temporary expansion view without text-owned structural features."""
    text_ids = {feature.id for feature in _text_features(program)}
    if not text_ids:
        return program
    features = tuple(feature for feature in program.features if feature.id not in text_ids)
    relations = tuple(
        relation
        for relation in program.relations
        if relation.subject_id not in text_ids and relation.object_id not in text_ids
    )
    return replace(program, features=features, relations=relations)


def strip_text_from_motor(motor: dict[str, Any], program: DesignSemanticProgram) -> None:
    """Remove compiled text nodes/templates so the structural mesh stays text-free."""
    text_ids = {str(feature.id) for feature in _text_features(program)}
    if not text_ids:
        return
    template_ids = {f"{feature_id}_template" for feature_id in text_ids}
    hierarchy = motor.get("hierarchy_program")
    if not isinstance(hierarchy, dict):
        return

    def prune(node: dict[str, Any]):
        node_id = str(node.get("id", ""))
        ids = {str(value) for value in node.get("template_ids", [])}
        if node_id in text_ids or ids.intersection(template_ids):
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

    roots = []
    for root in hierarchy.get("roots", []):
        if not isinstance(root, dict):
            roots.append(root)
            continue
        kept = prune(root)
        if kept is not None:
            roots.append(kept)
    hierarchy["roots"] = roots
    hierarchy["templates"] = [
        template
        for template in hierarchy.get("templates", [])
        if not isinstance(template, dict)
        or str(template.get("id", "")) not in template_ids
    ]


def uses_native_cylindrical_text(program: DesignSemanticProgram) -> bool:
    return program.body.family == "cylindrical" and bool(_text_features(program))


def _body_radius_from_motor(motor: dict[str, Any], program: DesignSemanticProgram) -> float:
    for field in motor.get("fields", []):
        if not isinstance(field, dict):
            continue
        if str(field.get("id")) == "body" and str(field.get("kind")) == "capped_cylinder":
            radii = field.get("radii")
            if isinstance(radii, list) and radii:
                radius = float(radii[0])
                if radius > 0.0:
                    return radius
    return 0.5 * float(program.body.width_mm)


def _mesh_surface_radius(stl_path: str | Path, fallback: float) -> float:
    mesh = trimesh.load_mesh(str(stl_path), process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
        return fallback
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    z_min, z_max = float(vertices[:, 2].min()), float(vertices[:, 2].max())
    span = max(z_max - z_min, 1.0e-9)
    z_fraction = (vertices[:, 2] - z_min) / span
    radial = np.linalg.norm(vertices[:, :2], axis=1)
    band = radial[(z_fraction >= 0.30) & (z_fraction <= 0.75)]
    if len(band) < 16:
        band = radial
    high = band[band >= np.quantile(band, 0.80)] if len(band) else band
    if len(high) == 0:
        return fallback
    measured = float(np.median(high))
    return measured if measured > 0.0 else fallback


def _vessel_z(motor: dict[str, Any], program: DesignSemanticProgram) -> tuple[float, float]:
    vessel = motor.get("vessel", {})
    if isinstance(vessel, dict):
        base = float(vessel.get("base_z_mm", 0.0))
        top = float(vessel.get("opening_start_z_mm", base + program.body.height_mm))
        if top > base:
            return base, top
    return 0.0, float(program.body.height_mm)


def _line_contract(program: DesignSemanticProgram):
    text_features = _text_features(program)
    source_prompt = getattr(program.source, "prompt", None)
    explicit_lines = _prompt_lines(source_prompt)
    if explicit_lines:
        feature = text_features[0]
        return tuple((feature, line) for line in explicit_lines)
    return tuple((feature, _text_core._literal_from_concept(feature.concept)) for feature in text_features)


def _native_text_tool(
    *,
    reference_radius: float,
    base_z: float,
    top_z: float,
    text_value: str,
    size_mm: float,
    depth_mm: float,
    u_offset_mm: float,
    v_center_mm: float,
) -> cq.Shape:
    height = top_z - base_z
    reference = cq.Solid.makeCylinder(
        reference_radius,
        height,
        cq.Vector(0.0, 0.0, base_z),
        cq.Vector(0.0, 0.0, 1.0),
    )
    surface = CylinderSurfaceMapper(radius=reference_radius)
    builder = NativeSurfaceTextBuilder()
    _projected, tool = builder._cylinder_text(
        base_shape=reference,
        surface=surface,
        text_value=text_value,
        size=size_mm,
        depth=depth_mm,
        mode="emboss",
        font="Arial",
        kind="regular",
        u_offset=u_offset_mm,
        v_offset=v_center_mm,
    )
    return tool


def decorate_mesh_result_with_native_text(
    mesh_result,
    motor: dict[str, Any],
    program: DesignSemanticProgram,
):
    """Apply existing native CAD text and return an updated vessel result."""
    if not uses_native_cylindrical_text(program):
        return mesh_result

    base_shape = load_advanced_stl_as_cadquery_shape(mesh_result.stl_path)
    fallback_radius = _body_radius_from_motor(motor, program)
    measured_radius = _mesh_surface_radius(mesh_result.stl_path, fallback_radius)

    # A small inward reference offset guarantees overlap with the triangulated
    # structural boundary while preserving the requested outward relief depth.
    embed_mm = min(0.30, max(0.10, 0.08 * program.manufacturing.minimum_wall_mm))
    reference_radius = max(1.0, measured_radius - embed_mm)
    base_z, top_z = _vessel_z(motor, program)
    usable_height = top_z - base_z

    contracts = _line_contract(program)
    if not contracts:
        return mesh_result

    first_feature = contracts[0][0]
    block_center = base_z + float(first_feature.anchor.vertical) * usable_height
    total_block_height = max(
        program.manufacturing.minimum_feature_mm,
        float(first_feature.size.height_ratio) * usable_height,
    )
    line_gap_ratio = 0.22
    slot_height = total_block_height / (
        len(contracts) + line_gap_ratio * max(len(contracts) - 1, 0)
    )
    gap = line_gap_ratio * slot_height
    block_top = block_center + 0.5 * total_block_height

    current = base_shape
    for index, (feature, literal) in enumerate(contracts):
        if len(contracts) == 1:
            v_center = base_z + float(feature.anchor.vertical) * usable_height
            size_mm = max(
                program.manufacturing.minimum_feature_mm,
                float(feature.size.height_ratio) * usable_height,
            )
        else:
            v_center = block_top - 0.5 * slot_height - index * (slot_height + gap)
            size_mm = slot_height

        circumference = 2.0 * np.pi * reference_radius
        u_offset = 0.25 * float(feature.anchor.horizontal) * circumference
        requested_depth = max(0.1, float(feature.size.depth_mm))
        tool = _native_text_tool(
            reference_radius=reference_radius,
            base_z=base_z,
            top_z=top_z,
            text_value=literal,
            size_mm=size_mm,
            depth_mm=requested_depth + embed_mm,
            u_offset_mm=u_offset,
            v_center_mm=v_center,
        )
        try:
            current = current.fuse(tool, tol=0.02).clean()
        except Exception as error:
            raise RuntimeError(
                f"Native CAD text boolean failed for '{literal}'."
            ) from error
        if not current.isValid():
            raise RuntimeError(f"Native CAD text produced invalid geometry for '{literal}'.")

    output_path = Path(mesh_result.stl_path)
    cq.exporters.export(
        current,
        str(output_path),
        tolerance=0.035,
        angularTolerance=0.08,
    )
    final_mesh = trimesh.load_mesh(str(output_path), process=False)
    if isinstance(final_mesh, trimesh.Scene):
        final_mesh = trimesh.util.concatenate(tuple(final_mesh.geometry.values()))
    if not isinstance(final_mesh, trimesh.Trimesh):
        raise RuntimeError("Native CAD text export did not produce a triangle mesh.")
    components = tuple(final_mesh.split(only_watertight=False))
    return replace(
        mesh_result,
        mesh=final_mesh,
        vertex_count=int(len(final_mesh.vertices)),
        face_count=int(len(final_mesh.faces)),
        component_count=len(components),
        volume_mm3=float(abs(final_mesh.volume)),
        watertight=bool(final_mesh.is_watertight),
        winding_consistent=bool(final_mesh.is_winding_consistent),
    )
