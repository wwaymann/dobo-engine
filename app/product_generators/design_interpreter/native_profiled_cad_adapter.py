from __future__ import annotations

"""Shared native CAD route for reusable revolved planter profiles.

Each catalog entry is a normalized radial section, not a product-specific
generator. The same revolve/shell/drain implementation builds every body.
"""

from pathlib import Path
from time import perf_counter
from typing import Any
import unicodedata

import cadquery as cq
import numpy as np
import trimesh

from product_generators.organic_shapes.vessel_engine import OrganicVesselResult

from .body_family_expansion import GeneralBodyFamilyExpander
from .design_pipeline import DoboDesignPipeline


PROFILED_CAD_ADAPTER_VERSION = "PCAD.2-smooth-dense-profile"
_PROFILED_ROUTE = "analytic_cad_profiled_revolution"
_PROFILE_SAMPLES_PER_SPAN = 10
_STL_TOLERANCE_MM = 0.02
_STL_ANGULAR_TOLERANCE_RAD = 0.045
_PREVIOUS_GENERATE = None
_PREVIOUS_EXPAND = None


PROFILE_CATALOG: dict[str, tuple[tuple[float, float], ...]] = {
    "amphora_tapered": (
        (0.00, 0.50), (0.10, 0.62), (0.40, 0.90),
        (0.72, 0.78), (0.88, 0.45), (1.00, 0.52),
    ),
    "urn_bellied": (
        (0.00, 0.58), (0.08, 0.68), (0.35, 1.00),
        (0.70, 0.88), (0.88, 0.55), (1.00, 0.62),
    ),
    "barrel": (
        (0.00, 0.75), (0.15, 0.90), (0.50, 1.00),
        (0.85, 0.90), (1.00, 0.76),
    ),
    "narrow_neck": (
        (0.00, 0.58), (0.12, 0.70), (0.55, 1.00),
        (0.82, 0.72), (0.92, 0.42), (1.00, 0.45),
    ),
    "flared_rim": (
        (0.00, 0.62), (0.15, 0.76), (0.65, 0.90),
        (0.88, 0.62), (0.96, 0.66), (1.00, 0.90),
    ),
    "inverted_taper": (
        (0.00, 0.55), (0.08, 0.58), (0.90, 0.86), (1.00, 0.95),
    ),
    "hourglass": (
        (0.00, 0.82), (0.12, 0.78), (0.50, 0.48),
        (0.85, 0.78), (1.00, 0.90),
    ),
    "tall_taper": (
        (0.00, 0.45), (0.10, 0.50), (0.85, 0.72), (1.00, 0.75),
    ),
    "oval_tall": (
        (0.00, 0.55), (0.12, 0.70), (0.50, 1.00),
        (0.88, 0.72), (1.00, 0.62),
    ),
    "pedestal_urn": (
        (0.00, 0.40), (0.08, 0.55), (0.20, 0.45),
        (0.45, 0.70), (0.78, 0.58), (0.92, 0.52), (1.00, 0.82),
    ),
}


PROFILE_ALIASES: dict[str, str] = {
    "amphora": "amphora_tapered",
    "amphora_tapered": "amphora_tapered",
    "anfora": "amphora_tapered",
    "anfora_ahusada": "amphora_tapered",
    "urn": "urn_bellied",
    "urn_bellied": "urn_bellied",
    "urna": "urn_bellied",
    "urna_globular": "urn_bellied",
    "barrel": "barrel",
    "barril": "barrel",
    "narrow_neck": "narrow_neck",
    "cuello_estrecho": "narrow_neck",
    "flared_rim": "flared_rim",
    "borde_ensanchado": "flared_rim",
    "inverted_taper": "inverted_taper",
    "tronco_invertido": "inverted_taper",
    "hourglass": "hourglass",
    "reloj_de_arena": "hourglass",
    "tall_taper": "tall_taper",
    "ahusada_alta": "tall_taper",
    "oval_tall": "oval_tall",
    "ovoide_alto": "oval_tall",
    "pedestal_urn": "pedestal_urn",
    "urna_pedestal": "pedestal_urn",
}


def _plain(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).strip().lower())
    return "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    ).replace("-", "_").replace(" ", "_")


def profile_variant(program) -> str | None:
    values = [_plain(tag) for tag in program.body.style_tags]
    values.append(_plain(program.body.family))
    for value in values:
        variant = PROFILE_ALIASES.get(value)
        if variant is not None:
            return variant
    return None


def _plain_motor(motor: dict[str, Any]) -> bool:
    hierarchy = motor.get("hierarchy_program", {})
    return (
        isinstance(hierarchy, dict)
        and not hierarchy.get("templates")
        and not hierarchy.get("roots")
    )


def _expand_with_profiled_cad(cls, motor: dict[str, Any], program):
    result = _PREVIOUS_EXPAND(cls, motor, program)
    variant = profile_variant(program)
    if variant is None:
        return result

    vessel = motor.get("vessel", {})
    if not isinstance(vessel, dict):
        raise RuntimeError("Profiled CAD route requires a vessel contract.")
    base_z = float(vessel.get("base_z_mm", 0.0))
    bottom = float(vessel.get("cavity_floor_z_mm", 0.0)) - base_z
    drain_radius = float(vessel.get("drain_radius_mm", 0.0))
    diameter = min(float(program.body.width_mm), float(program.body.depth_mm))

    motor["morphogenesis"]["profile"] = "profiled_revolution"
    motor["morphogenesis"]["profile_variant"] = variant
    motor["_profiled_revolution"] = {
        "adapter_version": PROFILED_CAD_ADAPTER_VERSION,
        "variant": variant,
        "diameter_mm": diameter,
        "height_mm": float(program.body.height_mm),
        "wall_mm": float(vessel.get("wall_mm", program.manufacturing.minimum_wall_mm)),
        "bottom_mm": bottom,
        "drain_required": drain_radius > 0.0,
        "drain_diameter_mm": 2.0 * drain_radius,
        "control_profile": [list(point) for point in PROFILE_CATALOG[variant]],
        "normalized_profile": [
            list(point) for point in _smooth_profile(PROFILE_CATALOG[variant])
        ],
        "profile_samples_per_span": _PROFILE_SAMPLES_PER_SPAN,
    }
    return result


def _smooth_profile(
    profile: tuple[tuple[float, float], ...],
    *,
    samples_per_span: int = _PROFILE_SAMPLES_PER_SPAN,
) -> tuple[tuple[float, float], ...]:
    """Densify a sparse vessel silhouette with a shape-preserving cubic curve.

    The catalog points remain the intentional design landmarks (foot, belly,
    shoulder, neck and rim).  PCHIP-style tangents add enough intermediate
    vertices to make those transitions visibly fluid without overshooting the
    radius range of either adjacent span.
    """
    if len(profile) < 2:
        raise ValueError("A profiled planter needs at least two control points.")
    samples = max(2, int(samples_per_span))
    z = [float(point[0]) for point in profile]
    radius = [float(point[1]) for point in profile]
    if any(z[index] <= z[index - 1] for index in range(1, len(z))):
        raise ValueError("Profile heights must be strictly increasing.")

    spacing = [z[index + 1] - z[index] for index in range(len(z) - 1)]
    slopes = [
        (radius[index + 1] - radius[index]) / spacing[index]
        for index in range(len(spacing))
    ]
    tangents = [0.0] * len(profile)
    tangents[0] = slopes[0]
    tangents[-1] = slopes[-1]
    for index in range(1, len(profile) - 1):
        before = slopes[index - 1]
        after = slopes[index]
        if before * after <= 0.0:
            tangents[index] = 0.0
            continue
        weight_before = 2.0 * spacing[index] + spacing[index - 1]
        weight_after = spacing[index] + 2.0 * spacing[index - 1]
        tangents[index] = (weight_before + weight_after) / (
            weight_before / before + weight_after / after
        )

    dense: list[tuple[float, float]] = []
    for index in range(len(profile) - 1):
        span = spacing[index]
        low = min(radius[index], radius[index + 1])
        high = max(radius[index], radius[index + 1])
        for step in range(samples):
            t = step / samples
            t2 = t * t
            t3 = t2 * t
            h00 = 2.0 * t3 - 3.0 * t2 + 1.0
            h10 = t3 - 2.0 * t2 + t
            h01 = -2.0 * t3 + 3.0 * t2
            h11 = t3 - t2
            value = (
                h00 * radius[index]
                + h10 * span * tangents[index]
                + h01 * radius[index + 1]
                + h11 * span * tangents[index + 1]
            )
            dense.append((z[index] + t * span, min(high, max(low, value))))
    dense.append((z[-1], radius[-1]))
    return tuple(dense)


def _radius_at(
    profile: tuple[tuple[float, float], ...],
    z_ratio: float,
) -> float:
    value = min(1.0, max(0.0, float(z_ratio)))
    for index in range(1, len(profile)):
        z0, r0 = profile[index - 1]
        z1, r1 = profile[index]
        if value <= z1:
            t = (value - z0) / max(z1 - z0, 1e-12)
            return r0 + t * (r1 - r0)
    return profile[-1][1]


def _revolved_polygon(
    points: list[tuple[float, float]],
    *,
    start_axis_z: float,
    end_axis_z: float,
) -> cq.Shape:
    workplane = cq.Workplane("XZ").moveTo(0.0, start_axis_z)
    workplane = workplane.lineTo(points[0][0], points[0][1])
    for radius, z in points[1:]:
        workplane = workplane.lineTo(radius, z)
    return (
        workplane
        .lineTo(0.0, end_axis_z)
        .close()
        .revolve(360.0, (0.0, start_axis_z), (0.0, end_axis_z))
        .val()
    )


def _profiled_body(route: dict[str, Any]) -> cq.Shape:
    height = float(route["height_mm"])
    maximum_radius = 0.5 * float(route["diameter_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    profile = tuple(
        (float(point[0]), float(point[1]))
        for point in route["normalized_profile"]
    )

    outer_points = [
        (maximum_radius * radius_ratio, height * z_ratio)
        for z_ratio, radius_ratio in profile
    ]
    outer = _revolved_polygon(
        outer_points,
        start_axis_z=0.0,
        end_axis_z=height,
    )

    cavity_start_ratio = min(1.0, max(0.0, bottom / height))
    inner_profile: list[tuple[float, float]] = [
        (
            max(0.5, maximum_radius * _radius_at(profile, cavity_start_ratio) - wall),
            bottom,
        )
    ]
    for z_ratio, radius_ratio in profile:
        z = height * z_ratio
        if z <= bottom + 1e-8:
            continue
        inner_profile.append((max(0.5, maximum_radius * radius_ratio - wall), z))
    inner_profile.append((inner_profile[-1][0], height + 1.0))
    cavity = _revolved_polygon(
        inner_profile,
        start_axis_z=bottom,
        end_axis_z=height + 1.0,
    )
    shape = outer.cut(cavity)

    if bool(route["drain_required"]):
        drain_radius = 0.5 * float(route["drain_diameter_mm"])
        drain = (
            cq.Workplane("XY")
            .workplane(offset=-1.0)
            .circle(drain_radius)
            .extrude(bottom + 2.0)
            .val()
        )
        shape = shape.cut(drain)

    shape = shape.clean()
    if not isinstance(shape, cq.Shape) or not shape.isValid():
        raise RuntimeError("Profiled CAD route produced invalid revolved geometry.")
    if len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Profiled CAD planter must contain exactly one solid.")
    return shape


def _inside(shape: cq.Shape, point: tuple[float, float, float]) -> bool:
    return bool(shape.isInside(cq.Vector(*point), 0.02))


def _load_mesh(path: str | Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(str(path), process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh.process(validate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("Profiled CAD route did not export a triangle mesh.")
    # OCC tessellates adjacent CAD faces independently.  Their shared seam can
    # differ by sub-micron numerical noise even though the source is one solid.
    # Welding at 1e-3 mm is still 20x tighter than the 0.02 mm STL tolerance and
    # prevents valid relief faces from being misclassified as extra components.
    mesh.merge_vertices(digits_vertex=3)
    mesh.remove_unreferenced_vertices()
    return mesh


def _generate_profiled(motor: dict[str, Any]) -> OrganicVesselResult:
    route = motor.get("_profiled_revolution")
    if not isinstance(route, dict):
        raise RuntimeError("Profiled CAD route is missing its contract.")

    started = perf_counter()
    shape = _profiled_body(route)
    output = motor["output"]
    output_dir = Path(str(output["directory"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = output_dir / f"{output['basename']}.stl"
    cq.exporters.export(
        shape,
        str(stl_path),
        tolerance=_STL_TOLERANCE_MM,
        angularTolerance=_STL_ANGULAR_TOLERANCE_RAD,
    )
    mesh = _load_mesh(stl_path)

    height = float(route["height_mm"])
    maximum_radius = 0.5 * float(route["diameter_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    profile = tuple(
        (float(point[0]), float(point[1]))
        for point in route["normalized_profile"]
    )
    mid_z = max(bottom + 1.0, 0.5 * height)
    outer_mid = maximum_radius * _radius_at(profile, mid_z / height)
    inner_mid = max(0.5, outer_mid - wall)
    wall_probe = 0.5 * (outer_mid + inner_mid)
    drain_radius = 0.5 * float(route["drain_diameter_mm"])
    base_outer = maximum_radius * _radius_at(profile, 0.5 * bottom / height)
    base_probe = min(
        base_outer - 0.75,
        max(drain_radius + 2.0, 0.55 * base_outer),
    )
    if base_probe <= drain_radius:
        base_probe = 0.5 * (drain_radius + base_outer)

    checks = {
        "outside_is_empty": not _inside(shape, (outer_mid + 2.0 * wall, 0.0, mid_z)),
        "wall_is_solid": _inside(shape, (wall_probe, 0.0, mid_z)),
        "cavity_is_empty": not _inside(shape, (0.0, 0.0, mid_z)),
        "opening_is_clear": not _inside(shape, (0.0, 0.0, height + 0.5)),
        "base_is_solid": _inside(shape, (base_probe, 0.0, 0.5 * bottom)),
        "drain_is_clear": (
            not _inside(shape, (0.0, 0.0, 0.5 * bottom))
            if bool(route["drain_required"])
            else True
        ),
        "below_base_is_empty": not _inside(shape, (base_probe, 0.0, -1.0)),
        "profile_is_revolved": True,
        "profile_variant_known": str(route["variant"]) in PROFILE_CATALOG,
    }

    elapsed = perf_counter() - started
    components = tuple(mesh.split(only_watertight=False))
    result = OrganicVesselResult(
        product_id=str(motor.get("id", "analytic_profiled")),
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
        flat_base_vertex_count=int(
            np.count_nonzero(np.abs(mesh.vertices[:, 2]) <= 0.08)
        ),
        semantic_checks=checks,
        mesh_quality=None,
        stage_seconds={"analytic_cad_profiled_revolution_export": elapsed},
        generation_seconds=elapsed,
        max_generation_seconds=float(output.get("max_generation_seconds", 45.0)),
    )
    result.validate()
    return result


def _generate_with_profiled(
    cls,
    motor_program: dict[str, Any],
    *,
    parser: Any,
    engine: Any,
):
    if (
        str(motor_program.get("morphogenesis", {}).get("profile", ""))
        == "profiled_revolution"
        and _plain_motor(motor_program)
    ):
        motor_program["_capability_route"] = _PROFILED_ROUTE
        result = _generate_profiled(motor_program)
        return result, motor_program, 1, "analytic_cad_profiled_revolution"
    return _PREVIOUS_GENERATE(
        cls,
        motor_program,
        parser=parser,
        engine=engine,
    )


def install_native_profiled_cad_adapter() -> str:
    global _PREVIOUS_GENERATE, _PREVIOUS_EXPAND
    current_generate = DoboDesignPipeline._generate_with_retry.__func__
    if not getattr(current_generate, "_dobo_profiled_cad_adapter", False):
        _PREVIOUS_GENERATE = current_generate
        _generate_with_profiled._dobo_profiled_cad_adapter = True
        DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_profiled)

    current_expand = GeneralBodyFamilyExpander.apply.__func__
    if not getattr(current_expand, "_dobo_profiled_cad_expansion", False):
        _PREVIOUS_EXPAND = current_expand
        _expand_with_profiled_cad._dobo_profiled_cad_expansion = True
        GeneralBodyFamilyExpander.apply = classmethod(_expand_with_profiled_cad)
    return PROFILED_CAD_ADAPTER_VERSION
