from __future__ import annotations

"""Analytic CAD route for DOBO tapered-revolution planters.

The semantic/body-family layer keeps deciding when a tapered primitive is
requested. This adapter only replaces the old stacked implicit approximation
for plain tapered vessels with DOBO's historical CadQuery loft body and drain.
Unsupported decorated/compound cases continue through the previous pipeline.
"""

from pathlib import Path
from time import perf_counter
from typing import Any

import cadquery as cq
import numpy as np
import trimesh

from engine.body import build_body
from engine.context import EngineContext
from engine.drain import build_drain
from product_generators.organic_shapes.vessel_engine import OrganicVesselResult

from .design_pipeline import DoboDesignPipeline


NATIVE_TAPERED_CAD_ADAPTER_VERSION = "NTAP.1-analytic-frustum"
_ANALYTIC_TAPERED_ROUTE = "analytic_cad_tapered_primitive"
_PREVIOUS_GENERATE_WITH_RETRY = None


def _plain_tapered_motor(motor: dict[str, Any]) -> bool:
    hierarchy = motor.get("hierarchy_program", {})
    if not isinstance(hierarchy, dict):
        return False
    return not hierarchy.get("templates") and not hierarchy.get("roots")


def _tapered_fields(motor: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = [
        field
        for field in motor.get("fields", [])
        if isinstance(field, dict)
        and (
            str(field.get("id")) == "body"
            or str(field.get("id", "")).startswith("tapered_body_")
        )
    ]
    if len(fields) < 2:
        raise RuntimeError("Tapered CAD route is missing canonical body sections.")

    def z_center(field: dict[str, Any]) -> float:
        center = field.get("center", [0.0, 0.0, 0.0])
        return float(center[2]) if isinstance(center, list) and len(center) >= 3 else 0.0

    ordered = sorted(fields, key=z_center)
    return ordered[0], ordered[-1]


def _section_radii(field: dict[str, Any]) -> tuple[float, float, float]:
    radii = field.get("radii", [])
    if not isinstance(radii, list) or len(radii) != 3:
        raise RuntimeError("Tapered CAD route received an invalid section radius contract.")
    rx, ry, rz = (float(radii[0]), float(radii[1]), float(radii[2]))
    if min(rx, ry, rz) <= 0.0:
        raise RuntimeError("Tapered CAD section radii must be positive.")
    return rx, ry, rz


def _tapered_dimensions_from_motor(
    motor: dict[str, Any],
) -> tuple[float, float, float]:
    lower, upper = _tapered_fields(motor)
    lower_rx, lower_ry, _ = _section_radii(lower)
    upper_rx, upper_ry, upper_rz = _section_radii(upper)

    # tapered_revolution is rotational. If an explicitly non-circular section
    # reaches this adapter, keep the existing volumetric route rather than
    # silently forcing an ellipse into a circular frustum.
    lower_mean = 0.5 * (lower_rx + lower_ry)
    upper_mean = 0.5 * (upper_rx + upper_ry)
    if abs(lower_rx - lower_ry) > 0.05 * lower_mean:
        raise RuntimeError("Tapered CAD lower section is not rotationally symmetric.")
    if abs(upper_rx - upper_ry) > 0.05 * upper_mean:
        raise RuntimeError("Tapered CAD upper section is not rotationally symmetric.")

    # GeneralBodyFamilyExpander's canonical tapered top section uses
    # axial radius 0.19 * semantic height. Recover that semantic height rather
    # than inheriting the old implicit envelope's approximate total span.
    height = upper_rz / 0.19
    bottom_diameter = 2.0 * lower_mean
    top_diameter = 2.0 * upper_mean
    if top_diameter <= bottom_diameter:
        raise RuntimeError("Tapered planter must be wider at the opening than at the base.")
    return bottom_diameter, top_diameter, height


def prepare_native_tapered_cad_route_from_motor(motor: dict[str, Any]) -> bool:
    morphology = motor.get("morphogenesis", {})
    if not isinstance(morphology, dict):
        return False
    if str(morphology.get("profile", "")) != "tapered_revolution":
        return False
    if not _plain_tapered_motor(motor):
        return False

    vessel = motor.get("vessel", {})
    if not isinstance(vessel, dict):
        raise RuntimeError("Native tapered CAD route requires vessel contract.")

    bottom_diameter, top_diameter, height = _tapered_dimensions_from_motor(motor)
    base_z = float(vessel.get("base_z_mm", 0.0))
    bottom_mm = float(vessel.get("cavity_floor_z_mm", 0.0)) - base_z
    drain_radius = float(vessel.get("drain_radius_mm", 0.0))

    motor["_capability_route"] = _ANALYTIC_TAPERED_ROUTE
    motor["_analytic_tapered"] = {
        "adapter_version": NATIVE_TAPERED_CAD_ADAPTER_VERSION,
        "profile": "tapered_revolution",
        "bottom_diameter_mm": bottom_diameter,
        "top_diameter_mm": top_diameter,
        "height_mm": height,
        "wall_mm": float(vessel.get("wall_mm", 3.0)),
        "bottom_mm": bottom_mm,
        "drain_required": drain_radius > 0.0,
        "drain_diameter_mm": 2.0 * drain_radius,
    }
    return True


def _inside(shape: cq.Shape, point: tuple[float, float, float]) -> bool:
    return bool(shape.isInside(cq.Vector(*point), 0.02))


def _load_welded_stl(path: str | Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(str(path), process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh.process(validate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("Native tapered CAD route did not export a triangle mesh.")
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def generate_native_tapered_cad_if_routed(
    motor: dict[str, Any],
) -> OrganicVesselResult | None:
    if motor.get("_capability_route") != _ANALYTIC_TAPERED_ROUTE:
        return None
    route = motor.get("_analytic_tapered")
    if not isinstance(route, dict):
        raise RuntimeError("Native tapered CAD route is missing its contract.")

    started = perf_counter()
    bottom_diameter = float(route["bottom_diameter_mm"])
    top_diameter = float(route["top_diameter_mm"])
    height = float(route["height_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    drain_diameter = float(route["drain_diameter_mm"])
    bottom_radius = 0.5 * bottom_diameter
    top_radius = 0.5 * top_diameter

    context = EngineContext({
        "top_diameter": top_diameter,
        "bottom_diameter": bottom_diameter,
        "height": height,
        "wall_thickness": wall,
        "bottom_thickness": bottom,
        "drain_hole": bool(route["drain_required"]),
        "drain_diameter": drain_diameter,
    })
    body = build_body(None, context)
    body = build_drain(body, context)
    shape = body.val().clean()
    if not isinstance(shape, cq.Shape) or not shape.isValid():
        raise RuntimeError("Historical CAD loft body/drain capability produced invalid tapered geometry.")
    if len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Analytic tapered planter must remain one CAD solid before tessellation.")

    output = motor.get("output", {})
    output_dir = Path(str(output["directory"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = output_dir / f"{output['basename']}.stl"
    cq.exporters.export(shape, str(stl_path), tolerance=0.035, angularTolerance=0.08)

    mesh = _load_welded_stl(stl_path)
    components = tuple(mesh.split(only_watertight=False))
    drain_radius = 0.5 * drain_diameter

    def outer_radius_at(z: float) -> float:
        t = min(1.0, max(0.0, z / height))
        return bottom_radius + t * (top_radius - bottom_radius)

    mid_z = max(bottom + 1.0, 0.5 * height)
    outer_mid = outer_radius_at(mid_z)
    inner_fraction = min(1.0, max(0.0, (mid_z - bottom) / height))
    inner_mid = (bottom_radius - wall) + inner_fraction * (
        (top_radius - wall) - (bottom_radius - wall)
    )
    wall_probe = 0.5 * (inner_mid + outer_mid)

    base_z = 0.5 * bottom
    base_outer = outer_radius_at(base_z)
    base_probe_x = min(
        base_outer - 0.75,
        max(drain_radius + 3.0, 0.45 * base_outer),
    )
    if base_probe_x <= drain_radius:
        base_probe_x = 0.5 * (drain_radius + base_outer)

    semantic_checks = {
        "outside_is_empty": not _inside(shape, (outer_mid + 2.0 * wall, 0.0, mid_z)),
        "wall_is_solid": _inside(shape, (wall_probe, 0.0, mid_z)),
        "cavity_is_empty": not _inside(shape, (0.0, 0.0, mid_z)),
        "opening_is_clear": not _inside(shape, (0.0, 0.0, height - 0.5)),
        "base_is_solid": _inside(shape, (base_probe_x, 0.0, base_z)),
        "drain_is_clear": (
            not _inside(shape, (0.0, 0.0, base_z))
            if bool(route["drain_required"])
            else True
        ),
        "below_base_is_empty": not _inside(shape, (base_probe_x, 0.0, -1.0)),
        "profile_is_tapered": top_diameter > bottom_diameter,
        "taper_is_monotonic": top_radius > outer_radius_at(0.5 * height) > bottom_radius,
        "dimensions_are_printable": (
            bottom_radius > wall
            and top_radius > wall
            and height > bottom
        ),
    }

    flat_count = int(np.count_nonzero(np.abs(mesh.vertices[:, 2]) <= 0.08))
    elapsed = perf_counter() - started
    result = OrganicVesselResult(
        product_id=str(motor.get("id", "analytic_tapered")),
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
        stage_seconds={"analytic_cad_tapered_body_drain_export": elapsed},
        generation_seconds=elapsed,
        max_generation_seconds=float(output.get("max_generation_seconds", 45.0)),
    )
    result.validate()
    return result


def _generate_with_native_tapered_cad(
    cls,
    motor_program: dict[str, Any],
    *,
    parser: Any,
    engine: Any,
):
    prepare_native_tapered_cad_route_from_motor(motor_program)
    native_result = generate_native_tapered_cad_if_routed(motor_program)
    if native_result is not None:
        return native_result, motor_program, 1, "analytic_cad_tapered_primitive"
    if _PREVIOUS_GENERATE_WITH_RETRY is None:
        raise RuntimeError("Native tapered CAD router was not installed correctly.")
    return _PREVIOUS_GENERATE_WITH_RETRY(
        cls,
        motor_program,
        parser=parser,
        engine=engine,
    )


def install_native_tapered_cad_adapter() -> str:
    global _PREVIOUS_GENERATE_WITH_RETRY
    current = DoboDesignPipeline._generate_with_retry.__func__
    if getattr(current, "_dobo_native_tapered_cad_adapter", False):
        return NATIVE_TAPERED_CAD_ADAPTER_VERSION
    _PREVIOUS_GENERATE_WITH_RETRY = current
    _generate_with_native_tapered_cad._dobo_native_tapered_cad_adapter = True
    DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_native_tapered_cad)
    return NATIVE_TAPERED_CAD_ADAPTER_VERSION
