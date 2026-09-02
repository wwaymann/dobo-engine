from __future__ import annotations

"""Analytic CAD routes for spherical and ovoid DOBO planter bodies.

These promoted radial families keep semantic interpretation and body-family
selection unchanged, but replace the old fused implicit blobs with a smooth
CadQuery loft shell. The body, cavity, open rim, flat base and centered drain
are generated as one exact CAD solid before STL tessellation.
"""

from pathlib import Path
from time import perf_counter
from typing import Any, Callable
import math

import cadquery as cq
import numpy as np
import trimesh

from product_generators.organic_shapes.vessel_engine import OrganicVesselResult

from .design_pipeline import DoboDesignPipeline


NATIVE_RADIAL_CAD_ADAPTER_VERSION = "NRAD.2-printable-tessellation"
_SPHERICAL_ROUTE = "analytic_cad_spherical_primitive"
_OVOID_ROUTE = "analytic_cad_ovoid_primitive"
_PREVIOUS_GENERATE_WITH_RETRY = None


def _plain_radial_motor(motor: dict[str, Any]) -> bool:
    hierarchy = motor.get("hierarchy_program", {})
    if not isinstance(hierarchy, dict):
        return False
    return not hierarchy.get("templates") and not hierarchy.get("roots")


def _field_by_id(motor: dict[str, Any], field_id: str) -> dict[str, Any]:
    for field in motor.get("fields", []):
        if isinstance(field, dict) and str(field.get("id")) == field_id:
            return field
    raise RuntimeError(f"Radial CAD route is missing canonical field {field_id!r}.")


def _radii(field: dict[str, Any]) -> tuple[float, float, float]:
    values = field.get("radii", [])
    if not isinstance(values, list) or len(values) != 3:
        raise RuntimeError("Radial CAD route received an invalid radius contract.")
    rx, ry, rz = (float(values[0]), float(values[1]), float(values[2]))
    if min(rx, ry, rz) <= 0.0:
        raise RuntimeError("Radial CAD field radii must be positive.")
    return rx, ry, rz


def _semantic_dimensions(motor: dict[str, Any], profile: str) -> tuple[float, float, float]:
    if profile == "spherical":
        rx, ry, rz = _radii(_field_by_id(motor, "spherical_mid"))
        return 2.0 * rx, 2.0 * ry, rz / 0.32
    if profile == "ovoid":
        rx, ry, rz = _radii(_field_by_id(motor, "ovoid_belly"))
        return rx / 0.49, ry / 0.48, rz / 0.34
    raise ValueError(f"Unsupported radial CAD profile: {profile!r}")


def prepare_native_radial_cad_route_from_motor(motor: dict[str, Any]) -> bool:
    morphology = motor.get("morphogenesis", {})
    if not isinstance(morphology, dict):
        return False
    profile = str(morphology.get("profile", ""))
    if profile not in {"spherical", "ovoid"} or not _plain_radial_motor(motor):
        return False

    vessel = motor.get("vessel", {})
    if not isinstance(vessel, dict):
        raise RuntimeError("Native radial CAD route requires vessel contract.")
    width, depth, height = _semantic_dimensions(motor, profile)
    wall = float(vessel.get("wall_mm", 3.0))
    base_z = float(vessel.get("base_z_mm", 0.0))
    bottom = float(vessel.get("cavity_floor_z_mm", 0.0)) - base_z
    opening = vessel.get("opening_radii", [])
    if not isinstance(opening, list) or len(opening) != 2:
        raise RuntimeError("Native radial CAD route requires opening radii.")
    opening_rx, opening_ry = float(opening[0]), float(opening[1])
    drain_radius = float(vessel.get("drain_radius_mm", 0.0))

    route = _SPHERICAL_ROUTE if profile == "spherical" else _OVOID_ROUTE
    motor["_capability_route"] = route
    motor["_analytic_radial"] = {
        "adapter_version": NATIVE_RADIAL_CAD_ADAPTER_VERSION,
        "profile": profile,
        "width_mm": width,
        "depth_mm": depth,
        "height_mm": height,
        "wall_mm": wall,
        "bottom_mm": bottom,
        "opening_rx_mm": opening_rx,
        "opening_ry_mm": opening_ry,
        "drain_required": drain_radius > 0.0,
        "drain_diameter_mm": 2.0 * drain_radius,
    }
    return True


def _sphere_scale(t: float, edge_scale: float) -> float:
    edge = min(0.88, max(0.28, float(edge_scale)))
    semi = 0.5 / math.sqrt(max(1e-8, 1.0 - edge * edge))
    q = (float(t) - 0.5) / semi
    return math.sqrt(max(edge * edge, 1.0 - q * q))


def _ovoid_scale(t: float, top_scale: float) -> float:
    top = min(0.82, max(0.34, float(top_scale)))
    controls = (
        (0.00, 0.46),
        (0.10, 0.60),
        (0.24, 0.82),
        (0.40, 0.98),
        (0.50, 1.00),
        (0.64, 0.93),
        (0.78, 0.80),
        (0.90, max(top + 0.07, 0.66)),
        (1.00, top),
    )
    t = min(1.0, max(0.0, float(t)))
    for (t0, s0), (t1, s1) in zip(controls, controls[1:]):
        if t <= t1:
            alpha = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            alpha = alpha * alpha * (3.0 - 2.0 * alpha)
            return s0 + alpha * (s1 - s0)
    return top


def _profile_functions(route: dict[str, Any]) -> tuple[Callable[[float], float], Callable[[float], float]]:
    profile = str(route["profile"])
    max_rx = 0.5 * float(route["width_mm"])
    max_ry = 0.5 * float(route["depth_mm"])
    wall = float(route["wall_mm"])
    top_rx = float(route["opening_rx_mm"]) + wall
    top_ry = float(route["opening_ry_mm"]) + wall
    sx = min(0.90, top_rx / max_rx)
    sy = min(0.90, top_ry / max_ry)

    if profile == "spherical":
        return (
            lambda t: max_rx * _sphere_scale(t, sx),
            lambda t: max_ry * _sphere_scale(t, sy),
        )
    if profile == "ovoid":
        return (
            lambda t: max_rx * _ovoid_scale(t, sx),
            lambda t: max_ry * _ovoid_scale(t, sy),
        )
    raise ValueError(f"Unsupported radial CAD profile: {profile!r}")


def _loft(sections: tuple[tuple[float, float, float], ...]) -> cq.Shape:
    if len(sections) < 2:
        raise ValueError("Radial loft needs at least two sections.")
    z0, rx0, ry0 = sections[0]
    work = cq.Workplane("XY").workplane(offset=float(z0)).ellipse(float(rx0), float(ry0))
    previous_z = float(z0)
    for z, rx, ry in sections[1:]:
        work = work.workplane(offset=float(z) - previous_z).ellipse(float(rx), float(ry))
        previous_z = float(z)
    shape = work.loft(combine=True, ruled=False).val().clean()
    if not isinstance(shape, cq.Shape) or not shape.isValid():
        raise RuntimeError("Analytic radial loft produced invalid CAD geometry.")
    return shape


def _build_radial_shape(route: dict[str, Any]) -> tuple[cq.Shape, Callable[[float], float], Callable[[float], float]]:
    height = float(route["height_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    rx_at, ry_at = _profile_functions(route)
    samples = (0.0, 0.08, 0.16, 0.26, 0.38, 0.50, 0.62, 0.74, 0.84, 0.92, 1.0)
    outer_sections = tuple((t * height, rx_at(t), ry_at(t)) for t in samples)
    outer = _loft(outer_sections)

    inner_t0 = min(0.95, max(0.02, bottom / height))
    inner_samples = tuple(t for t in samples if t > inner_t0)
    inner_t_values = (inner_t0, *inner_samples)
    inner_sections = []
    for t in inner_t_values:
        rx = rx_at(t) - wall
        ry = ry_at(t) - wall
        if min(rx, ry) <= 0.8:
            raise RuntimeError("Radial CAD wall leaves no valid cavity section.")
        inner_sections.append((t * height, rx, ry))
    _, top_rx, top_ry = inner_sections[-1]
    inner_sections.append((height + max(1.0, wall), top_rx, top_ry))
    inner = _loft(tuple(inner_sections))
    shape = outer.cut(inner, tol=0.01).clean()

    if bool(route["drain_required"]):
        drain_radius = 0.5 * float(route["drain_diameter_mm"])
        drain = cq.Workplane("XY").circle(drain_radius).extrude(bottom + max(1.0, wall)).val()
        shape = shape.cut(drain, tol=0.01).clean()

    if not shape.isValid() or len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Analytic radial planter must remain one valid CAD solid.")
    return shape, rx_at, ry_at


def _inside(shape: cq.Shape, point: tuple[float, float, float]) -> bool:
    return bool(shape.isInside(cq.Vector(*point), 0.02))


def _load_welded_stl(path: str | Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(str(path), process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh.process(validate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("Native radial CAD route did not export a triangle mesh.")
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def generate_native_radial_cad_if_routed(motor: dict[str, Any]) -> OrganicVesselResult | None:
    route_name = motor.get("_capability_route")
    if route_name not in {_SPHERICAL_ROUTE, _OVOID_ROUTE}:
        return None
    route = motor.get("_analytic_radial")
    if not isinstance(route, dict):
        raise RuntimeError("Native radial CAD route is missing its contract.")

    started = perf_counter()
    shape, rx_at, ry_at = _build_radial_shape(route)
    output = motor.get("output", {})
    output_dir = Path(str(output["directory"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = output_dir / f"{output['basename']}.stl"
    # Radial B-spline surfaces need a coarser tessellation than planes/cones.
    # 0.18 mm chord tolerance is well below normal FDM layer/nozzle scales for
    # these 100–125 mm planters, while avoiding six-figure STL meshes that add
    # no manufacturable detail and previously resembled the legacy voxel path.
    cq.exporters.export(shape, str(stl_path), tolerance=0.18, angularTolerance=0.22)
    mesh = _load_welded_stl(stl_path)
    components = tuple(mesh.split(only_watertight=False))

    height = float(route["height_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    drain_radius = 0.5 * float(route["drain_diameter_mm"])
    mid_t = 0.50
    mid_z = mid_t * height
    outer_mid = rx_at(mid_t)
    inner_mid = outer_mid - wall
    wall_probe = 0.5 * (outer_mid + inner_mid)
    base_t = min(0.95, max(0.0, 0.5 * bottom / height))
    base_outer = rx_at(base_t)
    base_probe_x = min(base_outer - 0.8, max(drain_radius + 3.0, 0.55 * base_outer))
    if base_probe_x <= drain_radius:
        base_probe_x = 0.5 * (drain_radius + base_outer)

    top_x = rx_at(1.0)
    bottom_x = rx_at(0.0)
    upper_x = rx_at(0.78)
    lower_x = rx_at(0.24)
    profile = str(route["profile"])
    semantic_checks = {
        "outside_is_empty": not _inside(shape, (outer_mid + 2.0 * wall, 0.0, mid_z)),
        "wall_is_solid": _inside(shape, (wall_probe, 0.0, mid_z)),
        "cavity_is_empty": not _inside(shape, (0.0, 0.0, mid_z)),
        "opening_is_clear": not _inside(shape, (0.0, 0.0, height - 0.5)),
        "base_is_solid": _inside(shape, (base_probe_x, 0.0, 0.5 * bottom)),
        "drain_is_clear": (
            not _inside(shape, (0.0, 0.0, 0.5 * bottom))
            if bool(route["drain_required"])
            else True
        ),
        "below_base_is_empty": not _inside(shape, (base_probe_x, 0.0, -1.0)),
        "profile_is_radial": outer_mid > max(top_x, bottom_x),
        "dimensions_are_printable": (
            min(float(route["width_mm"]), float(route["depth_mm"])) > 2.0 * wall
            and height > bottom
            and min(float(route["opening_rx_mm"]), float(route["opening_ry_mm"])) > drain_radius
        ),
    }
    if profile == "spherical":
        semantic_checks["profile_is_spherical"] = (
            abs(top_x - bottom_x) <= 0.03 * max(top_x, bottom_x)
            and outer_mid > 1.20 * top_x
        )
    else:
        semantic_checks["profile_is_ovoid"] = (
            outer_mid > lower_x
            and outer_mid > upper_x
            and upper_x > top_x
            and lower_x > bottom_x
        )

    flat_count = int(np.count_nonzero(np.abs(mesh.vertices[:, 2]) <= 0.08))
    elapsed = perf_counter() - started
    result = OrganicVesselResult(
        product_id=str(motor.get("id", f"analytic_{profile}")),
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
        stage_seconds={"analytic_cad_radial_body_cavity_drain_export": elapsed},
        generation_seconds=elapsed,
        max_generation_seconds=float(output.get("max_generation_seconds", 45.0)),
    )
    result.validate()
    return result


def _generate_with_native_radial_cad(
    cls,
    motor_program: dict[str, Any],
    *,
    parser: Any,
    engine: Any,
):
    prepare_native_radial_cad_route_from_motor(motor_program)
    native_result = generate_native_radial_cad_if_routed(motor_program)
    if native_result is not None:
        route = str(motor_program.get("_capability_route"))
        return native_result, motor_program, 1, route
    if _PREVIOUS_GENERATE_WITH_RETRY is None:
        raise RuntimeError("Native radial CAD router was not installed correctly.")
    return _PREVIOUS_GENERATE_WITH_RETRY(
        cls,
        motor_program,
        parser=parser,
        engine=engine,
    )


def install_native_radial_cad_adapter() -> str:
    global _PREVIOUS_GENERATE_WITH_RETRY
    current = DoboDesignPipeline._generate_with_retry.__func__
    if getattr(current, "_dobo_native_radial_cad_adapter", False):
        return NATIVE_RADIAL_CAD_ADAPTER_VERSION
    _PREVIOUS_GENERATE_WITH_RETRY = current
    _generate_with_native_radial_cad._dobo_native_radial_cad_adapter = True
    DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_native_radial_cad)
    return NATIVE_RADIAL_CAD_ADAPTER_VERSION
