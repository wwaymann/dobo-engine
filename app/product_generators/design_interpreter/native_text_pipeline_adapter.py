from __future__ import annotations

"""Capability router for cylindrical DOBO text.

Compatible cylindrical planters stay in DOBO's historical CadQuery body/drain
representation, receive DOBO's existing native surface text, and are tessellated
only for final STL/3MF output. Unsupported compositions keep the existing
structural/volumetric route rather than silently losing features.
"""

from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any
import math
import unicodedata

import cadquery as cq
import numpy as np
import trimesh

from engine.body import build_body
from engine.context import EngineContext
from engine.drain import build_drain
from product_generators.organic_shapes.vessel_engine import OrganicVesselResult
from product_generators.surface_designer.advanced_body_adapter import (
    load_advanced_stl_as_cadquery_shape,
)
from product_generators.surface_designer.native_text import NativeSurfaceTextBuilder
from product_generators.surface_mapping.cylinder_mapper import CylinderSurfaceMapper

from . import core_capability_reconnection as _text_core
from .design_pipeline import DoboDesignPipeline
from .semantic_contract import DesignSemanticProgram
from .text_surface_consolidation import _prompt_lines


NATIVE_TEXT_PIPELINE_ADAPTER_VERSION = "NTC.2-analytic-capability-routing"
_ANALYTIC_ROUTE = "analytic_cad_cylindrical_text"
_ORIGINAL_GENERATE_WITH_RETRY = DoboDesignPipeline._generate_with_retry.__func__


def _text_features(program: DesignSemanticProgram):
    return tuple(feature for feature in program.features if feature.form_hint == "text")


def body_program_without_text(program: DesignSemanticProgram) -> DesignSemanticProgram:
    text_ids = {feature.id for feature in _text_features(program)}
    if not text_ids:
        return program
    return replace(
        program,
        features=tuple(feature for feature in program.features if feature.id not in text_ids),
        relations=tuple(
            relation
            for relation in program.relations
            if relation.subject_id not in text_ids and relation.object_id not in text_ids
        ),
    )


def _plain(value: object) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _plumbing_feature(feature) -> bool:
    value = f"{getattr(feature, 'id', '')}_{getattr(feature, 'concept', '')}"
    tokens = set(_plain(value).replace("-", "_").replace(" ", "_").split("_"))
    return bool(tokens & {
        "drain", "drainage", "drenaje", "agujero",
        "opening", "abertura", "apertura", "boca",
        "cavity", "cavidad", "hueco", "hollow", "interior",
    })


def uses_native_cylindrical_text(program: DesignSemanticProgram) -> bool:
    return program.body.family == "cylindrical" and bool(_text_features(program))


def _supports_analytic_route(program: DesignSemanticProgram) -> bool:
    if not uses_native_cylindrical_text(program):
        return False
    unsupported = tuple(
        feature
        for feature in program.features
        if feature.form_hint != "text" and not _plumbing_feature(feature)
    )
    return not unsupported


def _line_contract(program: DesignSemanticProgram):
    text_features = _text_features(program)
    explicit_lines = _prompt_lines(getattr(program.source, "prompt", None))
    if explicit_lines:
        feature = text_features[0]
        return tuple((feature, line) for line in explicit_lines)
    return tuple(
        (feature, _text_core._literal_from_concept(feature.concept))
        for feature in text_features
    )


def _analytic_route_payload(motor: dict[str, Any], program: DesignSemanticProgram) -> dict[str, Any]:
    vessel = motor.get("vessel", {})
    if not isinstance(vessel, dict):
        raise RuntimeError("Analytic cylindrical route requires vessel contract.")
    base_z = float(vessel.get("base_z_mm", 0.0))
    bottom_mm = float(vessel.get("cavity_floor_z_mm", 0.0)) - base_z
    diameter = 0.5 * (float(program.body.width_mm) + float(program.body.depth_mm))
    entries = []
    for feature, literal in _line_contract(program):
        entries.append({
            "literal": literal,
            "horizontal": float(feature.anchor.horizontal),
            "vertical": float(feature.anchor.vertical),
            "height_ratio": float(feature.size.height_ratio),
            "depth_mm": float(feature.size.depth_mm),
            "mode": "deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss",
        })
    return {
        "diameter_mm": diameter,
        "height_mm": float(program.body.height_mm),
        "wall_mm": float(vessel.get("wall_mm", program.manufacturing.minimum_wall_mm)),
        "bottom_mm": bottom_mm,
        "drain_required": bool(program.manufacturing.drainage_required),
        "drain_diameter_mm": 2.0 * float(vessel.get("drain_radius_mm", 2.0)),
        "minimum_feature_mm": float(program.manufacturing.minimum_feature_mm),
        "text_entries": entries,
    }


def strip_text_from_motor(motor: dict[str, Any], program: DesignSemanticProgram) -> None:
    """Keep text semantic intent but remove text nodes from volumetric hierarchy."""
    text_ids = {str(feature.id) for feature in _text_features(program)}
    if not text_ids:
        return
    template_ids = {f"{feature_id}_template" for feature_id in text_ids}
    hierarchy = motor.get("hierarchy_program")
    if isinstance(hierarchy, dict):
        def prune(node: dict[str, Any]):
            node_id = str(node.get("id", ""))
            ids = {str(value) for value in node.get("template_ids", [])}
            if node_id in text_ids or ids.intersection(template_ids):
                return None
            cleaned = dict(node)
            children = []
            for child in node.get("children", []):
                if isinstance(child, dict):
                    kept_child = prune(child)
                    if kept_child is not None:
                        children.append(kept_child)
                else:
                    children.append(child)
            cleaned["children"] = children
            return cleaned

        roots = []
        for root in hierarchy.get("roots", []):
            if isinstance(root, dict):
                kept_root = prune(root)
                if kept_root is not None:
                    roots.append(kept_root)
            else:
                roots.append(root)
        hierarchy["roots"] = roots
        hierarchy["templates"] = [
            template
            for template in hierarchy.get("templates", [])
            if not isinstance(template, dict)
            or str(template.get("id", "")) not in template_ids
        ]

    if _supports_analytic_route(program):
        motor["_capability_route"] = _ANALYTIC_ROUTE
        motor["_analytic_cylindrical"] = _analytic_route_payload(motor, program)


def _inside(shape: cq.Shape, point: tuple[float, float, float]) -> bool:
    return bool(shape.isInside(cq.Vector(*point), 0.02))


def _load_welded_stl(path: str | Path) -> trimesh.Trimesh:
    """Load STL with coincident CAD tessellation vertices welded for topology checks."""
    mesh = trimesh.load_mesh(str(path), process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh.process(validate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("CAD route did not export a triangle mesh.")
    # CAD/STL tessellation emits coincident vertices independently per face.
    # Merge them before connected-component/watertight validation; otherwise
    # a single valid CAD solid can be misreported as many disconnected shells.
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def _apply_native_text(shape: cq.Shape, route: dict[str, Any]) -> cq.Shape:
    entries = tuple(route.get("text_entries", []))
    if not entries:
        return shape

    radius = 0.5 * float(route["diameter_mm"])
    height = float(route["height_mm"])
    minimum_feature = float(route["minimum_feature_mm"])
    surface = CylinderSurfaceMapper(radius=radius)
    builder = NativeSurfaceTextBuilder()

    first = entries[0]
    block_center = float(first["vertical"]) * height
    total_block_height = max(minimum_feature, float(first["height_ratio"]) * height)
    gap_ratio = 0.22
    slot_height = total_block_height / (len(entries) + gap_ratio * max(len(entries) - 1, 0))
    gap = gap_ratio * slot_height
    block_top = block_center + 0.5 * total_block_height

    current = shape
    for index, entry in enumerate(entries):
        if len(entries) == 1:
            v_offset = float(entry["vertical"]) * height
            size = max(minimum_feature, float(entry["height_ratio"]) * height)
        else:
            v_offset = block_top - 0.5 * slot_height - index * (slot_height + gap)
            size = slot_height
        u_offset = 0.25 * float(entry["horizontal"]) * (2.0 * math.pi * radius)
        result = builder.apply(
            base_shape=current,
            surface=surface,
            text_value=str(entry["literal"]),
            size=size,
            depth=max(0.1, float(entry["depth_mm"])),
            mode=str(entry["mode"]),
            font="Arial",
            kind="regular",
            u_offset=u_offset,
            v_offset=v_offset,
        )
        current = result.shape
    return current


def _generate_analytic_cylindrical(motor: dict[str, Any]) -> OrganicVesselResult:
    route = motor.get("_analytic_cylindrical")
    if not isinstance(route, dict):
        raise RuntimeError("Analytic cylindrical capability route is missing its contract.")

    started = perf_counter()
    diameter = float(route["diameter_mm"])
    radius = 0.5 * diameter
    height = float(route["height_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    drain_diameter = float(route["drain_diameter_mm"])

    context = EngineContext({
        "top_diameter": diameter,
        "bottom_diameter": diameter,
        "height": height,
        "wall_thickness": wall,
        "bottom_thickness": bottom,
        "drain_hole": bool(route["drain_required"]),
        "drain_diameter": drain_diameter,
    })

    body = build_body(None, context)
    body = build_drain(body, context)
    shape = body.val()
    if not isinstance(shape, cq.Shape) or not shape.isValid():
        raise RuntimeError("Historical CAD body/drain capability produced invalid geometry.")

    shape = _apply_native_text(shape, route).clean()
    if not shape.isValid():
        raise RuntimeError("Native CAD text produced invalid analytic planter geometry.")
    if len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Analytic planter must remain one CAD solid before tessellation.")

    output = motor.get("output", {})
    output_dir = Path(str(output["directory"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = output_dir / f"{output['basename']}.stl"
    cq.exporters.export(shape, str(stl_path), tolerance=0.035, angularTolerance=0.08)

    mesh = _load_welded_stl(stl_path)
    components = tuple(mesh.split(only_watertight=False))
    drain_radius = 0.5 * drain_diameter
    base_ring_x = max(drain_radius + 3.0, 0.25 * radius)
    mid_z = max(bottom + 1.0, 0.5 * height)
    semantic_checks = {
        "outside_is_empty": not _inside(shape, (radius + 2.0 * wall, 0.0, mid_z)),
        "wall_is_solid": _inside(shape, (radius - 0.5 * wall, 0.0, mid_z)),
        "cavity_is_empty": not _inside(shape, (0.0, 0.0, mid_z)),
        "opening_is_clear": not _inside(shape, (0.0, 0.0, height + 1.0)),
        "base_ring_is_solid": _inside(shape, (base_ring_x, 0.0, 0.5 * bottom)),
        "drain_is_clear": (
            not _inside(shape, (0.0, 0.0, 0.5 * bottom))
            if bool(route["drain_required"])
            else True
        ),
        "below_base_is_empty": not _inside(shape, (base_ring_x, 0.0, -1.0)),
    }

    flat_tolerance = 0.08
    flat_count = int(np.count_nonzero(np.abs(mesh.vertices[:, 2]) <= flat_tolerance))
    result = OrganicVesselResult(
        product_id=str(motor.get("id", "analytic_cylindrical")),
        mesh=mesh,
        stl_path=str(stl_path),
        vertex_count=int(len(mesh.vertices)),
        face_count=int(len(mesh.faces)),
        component_count=len(components),
        volume_mm3=float(abs(mesh.volume)),
        watertight=bool(mesh.is_watertight),
        winding_consistent=bool(mesh.is_winding_consistent),
        nominal_wall_mm=wall,
        bottom_mm=bottom,
        flat_base_z_mm=0.0,
        flat_base_vertex_count=flat_count,
        semantic_checks=semantic_checks,
        mesh_quality=None,
        stage_seconds={"analytic_cad_body_drain_text_export": perf_counter() - started},
        generation_seconds=perf_counter() - started,
        max_generation_seconds=float(output.get("max_generation_seconds", 45.0)),
    )
    result.validate()
    return result


def _generate_with_capability_route(
    cls,
    motor_program: dict[str, Any],
    *,
    parser: Any,
    engine: Any,
):
    if motor_program.get("_capability_route") == _ANALYTIC_ROUTE:
        result = _generate_analytic_cylindrical(motor_program)
        return result, motor_program, 1, "analytic_cad_native_text"
    return _ORIGINAL_GENERATE_WITH_RETRY(
        cls,
        motor_program,
        parser=parser,
        engine=engine,
    )


def _body_radius_from_motor(motor: dict[str, Any], program: DesignSemanticProgram) -> float:
    for field in motor.get("fields", []):
        if isinstance(field, dict) and str(field.get("id")) == "body" and str(field.get("kind")) == "capped_cylinder":
            radii = field.get("radii")
            if isinstance(radii, list) and radii and float(radii[0]) > 0.0:
                return float(radii[0])
    return 0.5 * float(program.body.width_mm)


def _mesh_surface_radius(stl_path: str | Path, fallback: float) -> float:
    mesh = _load_welded_stl(stl_path)
    if len(mesh.vertices) == 0:
        return fallback
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    radial = np.linalg.norm(vertices[:, :2], axis=1)
    high = radial[radial >= np.quantile(radial, 0.80)]
    return float(np.median(high)) if len(high) else fallback


def decorate_mesh_result_with_native_text(mesh_result, motor: dict[str, Any], program: DesignSemanticProgram):
    """Fallback bridge for cylindrical text cases not eligible for analytic routing."""
    if not uses_native_cylindrical_text(program):
        return mesh_result
    if motor.get("_capability_route") == _ANALYTIC_ROUTE:
        return mesh_result

    base_shape = load_advanced_stl_as_cadquery_shape(mesh_result.stl_path)
    radius = _mesh_surface_radius(mesh_result.stl_path, _body_radius_from_motor(motor, program))
    current = base_shape
    builder = NativeSurfaceTextBuilder()
    surface = CylinderSurfaceMapper(radius=radius)
    contracts = _line_contract(program)
    for feature, literal in contracts:
        current = builder.apply(
            base_shape=current,
            surface=surface,
            text_value=literal,
            size=max(program.manufacturing.minimum_feature_mm, feature.size.height_ratio * program.body.height_mm),
            depth=max(0.1, feature.size.depth_mm),
            mode="deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss",
            u_offset=0.25 * feature.anchor.horizontal * (2.0 * math.pi * radius),
            v_offset=feature.anchor.vertical * program.body.height_mm,
        ).shape

    output_path = Path(mesh_result.stl_path)
    cq.exporters.export(current, str(output_path), tolerance=0.035, angularTolerance=0.08)
    final_mesh = _load_welded_stl(output_path)
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


DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_capability_route)
