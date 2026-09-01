from __future__ import annotations

"""Native CAD routing for simple angular planter bodies.

This adapter does not introduce a second geometry engine. It reconnects the
consolidated semantic/structural pipeline to the same historical CadQuery body
and drain capabilities already used by the analytic cylindrical text route.
Complex or decorated bodies remain on the existing volumetric path.
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


NATIVE_CAD_PRIMITIVE_ADAPTER_VERSION = "NCAP.2-motor-router"
_ANALYTIC_ANGULAR_ROUTE = "analytic_cad_angular_primitive"
_PREVIOUS_GENERATE_WITH_RETRY = None


def _plain_angular_motor(motor: dict[str, Any]) -> bool:
    hierarchy = motor.get("hierarchy_program", {})
    if not isinstance(hierarchy, dict):
        return False
    return not hierarchy.get("templates") and not hierarchy.get("roots")


def _angular_dimensions_from_motor(
    motor: dict[str, Any],
    profile: str,
) -> tuple[float, float, float]:
    fields = {
        str(field.get("id")): field
        for field in motor.get("fields", [])
        if isinstance(field, dict)
    }
    if profile == "cuboid":
        field = fields.get("body")
        if not isinstance(field, dict):
            raise RuntimeError("Cuboid CAD route is missing body field.")
        radii = field.get("radii", [])
        if len(radii) != 3:
            raise RuntimeError("Cuboid CAD route has invalid body radii.")
        width = float(radii[0]) / 0.49
        depth = float(radii[1]) / 0.49
        height = float(radii[2]) / 0.29
        return width, depth, height

    if profile == "rectangular_prism":
        field = fields.get("rectangular_mid")
        if not isinstance(field, dict):
            raise RuntimeError("Rectangular CAD route is missing mid field.")
        radii = field.get("radii", [])
        if len(radii) != 3:
            raise RuntimeError("Rectangular CAD route has invalid mid radii.")
        width = float(radii[0]) / 0.49
        depth = float(radii[1]) / 0.48
        height = float(radii[2]) / 0.29
        return width, depth, height

    raise RuntimeError(f"Unsupported native CAD angular profile: {profile!r}")


def prepare_native_cad_primitive_route_from_motor(motor: dict[str, Any]) -> bool:
    morphology = motor.get("morphogenesis", {})
    if not isinstance(morphology, dict):
        return False
    profile = str(morphology.get("profile", ""))
    if profile not in {"cuboid", "rectangular_prism"}:
        return False
    if not _plain_angular_motor(motor):
        return False

    vessel = motor.get("vessel", {})
    if not isinstance(vessel, dict):
        raise RuntimeError("Native CAD primitive route requires vessel contract.")
    width, depth, height = _angular_dimensions_from_motor(motor, profile)
    base_z = float(vessel.get("base_z_mm", 0.0))
    bottom_mm = float(vessel.get("cavity_floor_z_mm", 0.0)) - base_z
    drain_radius = float(vessel.get("drain_radius_mm", 0.0))

    motor["_capability_route"] = _ANALYTIC_ANGULAR_ROUTE
    motor["_analytic_angular"] = {
        "adapter_version": NATIVE_CAD_PRIMITIVE_ADAPTER_VERSION,
        "profile": profile,
        "width_mm": width,
        "depth_mm": depth,
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
        raise RuntimeError("Native CAD primitive route did not export a triangle mesh.")
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def generate_native_cad_primitive_if_routed(
    motor: dict[str, Any],
) -> OrganicVesselResult | None:
    if motor.get("_capability_route") != _ANALYTIC_ANGULAR_ROUTE:
        return None

    route = motor.get("_analytic_angular")
    if not isinstance(route, dict):
        raise RuntimeError("Native CAD angular route is missing its contract.")

    started = perf_counter()
    width = float(route["width_mm"])
    depth = float(route["depth_mm"])
    height = float(route["height_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    drain_diameter = float(route["drain_diameter_mm"])

    context = EngineContext({
        "body_shape": str(route["profile"]),
        "width": width,
        "depth": depth,
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
        raise RuntimeError("Native CAD body/drain capability produced invalid angular geometry.")
    if len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Native CAD angular planter must remain one solid before tessellation.")

    output = motor.get("output", {})
    output_dir = Path(str(output["directory"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = output_dir / f"{output['basename']}.stl"
    cq.exporters.export(shape, str(stl_path), tolerance=0.035, angularTolerance=0.08)

    mesh = _load_welded_stl(stl_path)
    components = tuple(mesh.split(only_watertight=False))
    drain_radius = 0.5 * drain_diameter
    mid_z = max(bottom + 1.0, 0.5 * height)
    half_width = 0.5 * width
    base_probe_x = min(
        half_width - wall - 1.0,
        max(drain_radius + 3.0, 0.25 * width),
    )
    if base_probe_x <= drain_radius:
        base_probe_x = 0.5 * (drain_radius + max(drain_radius + 0.5, half_width - wall))

    semantic_checks = {
        "outside_is_empty": not _inside(shape, (half_width + 2.0 * wall, 0.0, mid_z)),
        "wall_is_solid": _inside(shape, (half_width - 0.5 * wall, 0.0, mid_z)),
        "cavity_is_empty": not _inside(shape, (0.0, 0.0, mid_z)),
        "opening_is_clear": not _inside(shape, (0.0, 0.0, height + 1.0)),
        "base_is_solid": _inside(shape, (base_probe_x, 0.0, 0.5 * bottom)),
        "drain_is_clear": (
            not _inside(shape, (0.0, 0.0, 0.5 * bottom))
            if bool(route["drain_required"])
            else True
        ),
        "below_base_is_empty": not _inside(shape, (base_probe_x, 0.0, -1.0)),
        "dimensions_are_rectangular": width > 2.0 * wall and depth > 2.0 * wall,
        "profile_is_angular": str(route["profile"]) in {"cuboid", "rectangular_prism"},
    }

    flat_count = int(np.count_nonzero(np.abs(mesh.vertices[:, 2]) <= 0.08))
    elapsed = perf_counter() - started
    result = OrganicVesselResult(
        product_id=str(motor.get("id", "analytic_angular")),
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
        stage_seconds={"analytic_cad_angular_body_drain_export": elapsed},
        generation_seconds=elapsed,
        max_generation_seconds=float(output.get("max_generation_seconds", 45.0)),
    )
    result.validate()
    return result


def _generate_with_native_cad_primitive(
    cls,
    motor_program: dict[str, Any],
    *,
    parser: Any,
    engine: Any,
):
    prepare_native_cad_primitive_route_from_motor(motor_program)
    native_result = generate_native_cad_primitive_if_routed(motor_program)
    if native_result is not None:
        return native_result, motor_program, 1, "analytic_cad_native_primitive"
    if _PREVIOUS_GENERATE_WITH_RETRY is None:
        raise RuntimeError("Native CAD primitive router was not installed correctly.")
    return _PREVIOUS_GENERATE_WITH_RETRY(
        cls,
        motor_program,
        parser=parser,
        engine=engine,
    )


def install_native_cad_primitive_adapter() -> str:
    global _PREVIOUS_GENERATE_WITH_RETRY
    current = DoboDesignPipeline._generate_with_retry.__func__
    if getattr(current, "_dobo_native_cad_primitive_adapter", False):
        return NATIVE_CAD_PRIMITIVE_ADAPTER_VERSION
    _PREVIOUS_GENERATE_WITH_RETRY = current
    _generate_with_native_cad_primitive._dobo_native_cad_primitive_adapter = True
    DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_native_cad_primitive)
    return NATIVE_CAD_PRIMITIVE_ADAPTER_VERSION
