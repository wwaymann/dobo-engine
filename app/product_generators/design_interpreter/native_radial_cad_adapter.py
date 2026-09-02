from __future__ import annotations

"""Analytic CAD routes for spherical and ovoid DOBO planter bodies.

These promoted radial families keep semantic interpretation and body-family
selection unchanged, but replace the old fused implicit blobs with smooth
revolved CAD profiles. The spherical body uses a true circular meridian; the
ovoid uses one continuous parametric spline meridian. Body, cavity, open rim,
flat base and centered drain remain one exact CAD solid before STL tessellation.
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


NATIVE_RADIAL_CAD_ADAPTER_VERSION = "NRAD.3-smooth-revolution"
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
        "surface_model": "revolved_circle" if profile == "spherical" else "revolved_spline",
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


def _hermite(y0: float, y1: float, m0: float, m1: float, s: float) -> float:
    s = min(1.0, max(0.0, float(s)))
    h00 = 2.0 * s**3 - 3.0 * s**2 + 1.0
    h10 = s**3 - 2.0 * s**2 + s
    h01 = -2.0 * s**3 + 3.0 * s**2
    h11 = s**3 - s**2
    return h00 * y0 + h10 * m0 + h01 * y1 + h11 * m1


def _ovoid_scale(t: float, top_scale: float) -> float:
    """Smooth asymmetric ovoid meridian without a conical lower transition."""

    top = min(0.82, max(0.34, float(top_scale)))
    peak_t = 0.46
    bottom = 0.66
    t = min(1.0, max(0.0, float(t)))
    if t <= peak_t:
        s = t / peak_t
        return _hermite(bottom, 1.0, 0.18, 0.0, s)
    s = (t - peak_t) / (1.0 - peak_t)
    return _hermite(1.0, top, 0.0, -0.12, s)


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


def _scale_y(shape: cq.Shape, scale_y: float) -> cq.Shape:
    if abs(float(scale_y) - 1.0) <= 1e-9:
        return shape
    matrix = cq.Matrix(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, float(scale_y), 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    transformed = shape.transformGeometry(matrix).clean()
    if not transformed.isValid():
        raise RuntimeError("Radial CAD elliptic scaling produced invalid geometry.")
    return transformed


def _revolved_parametric_profile(
    radius_at: Callable[[float], float],
    *,
    height: float,
    start_t: float,
    wall_offset: float = 0.0,
    extend_top: float = 0.0,
) -> cq.Shape:
    start_t = min(1.0, max(0.0, float(start_t)))

    def point(t: float) -> tuple[float, float]:
        radius = float(radius_at(t)) - float(wall_offset)
        if radius <= 0.8:
            raise RuntimeError("Radial CAD wall leaves no valid profile radius.")
        return radius, float(height) * float(t)

    work = cq.Workplane("XZ").parametricCurve(
        point,
        N=80,
        start=start_t,
        stop=1.0,
        tol=1e-4,
        maxDeg=6,
        smoothing=(1.0, 1.0, 1.0),
        makeWire=False,
    )
    top_radius = point(1.0)[0]
    top_z = float(height)
    if extend_top > 0.0:
        top_z += float(extend_top)
        work = work.lineTo(top_radius, top_z)
    work = work.lineTo(0.0, top_z).lineTo(0.0, float(height) * start_t).close()
    shape = work.revolve(360.0, (0.0, 0.0), (0.0, 1.0)).val().clean()
    if not isinstance(shape, cq.Shape) or not shape.isValid():
        raise RuntimeError("Smooth radial revolution produced invalid CAD geometry.")
    return shape


def _build_radial_shape(route: dict[str, Any]) -> tuple[cq.Shape, Callable[[float], float], Callable[[float], float]]:
    height = float(route["height_mm"])
    width = float(route["width_mm"])
    depth = float(route["depth_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    profile = str(route["profile"])
    rx_at, ry_at = _profile_functions(route)

    if profile == "spherical":
        outer = (
            cq.Workplane("XZ")
            .moveTo(rx_at(0.0), 0.0)
            .threePointArc((rx_at(0.5), 0.5 * height), (rx_at(1.0), height))
            .lineTo(0.0, height)
            .lineTo(0.0, 0.0)
            .close()
            .revolve(360.0, (0.0, 0.0), (0.0, 1.0))
            .val()
            .clean()
        )
    elif profile == "ovoid":
        outer = _revolved_parametric_profile(
            rx_at,
            height=height,
            start_t=0.0,
        )
    else:
        raise ValueError(f"Unsupported radial CAD profile: {profile!r}")

    aspect_y = depth / width
    outer = _scale_y(outer, aspect_y)

    inner_t0 = min(0.95, max(0.02, bottom / height))
    inner = _revolved_parametric_profile(
        rx_at,
        height=height,
        start_t=inner_t0,
        wall_offset=wall,
        extend_top=max(1.0, wall),
    )
    inner = _scale_y(inner, aspect_y)
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
    cq.exporters.export(shape, str(stl_path), tolerance=0.08, angularTolerance=0.08)
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
        "surface_is_continuous_revolution": str(route.get("surface_model", "")).startswith("revolved_"),
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
            and bottom_x > 0.60 * outer_mid
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
