from __future__ import annotations

"""Shared native CAD route for reusable revolved planter profiles.

Each catalog entry is a normalized radial section, not a product-specific
generator. The same revolve/shell/drain implementation builds every body.
"""

from pathlib import Path
from time import perf_counter
from typing import Any
import math

from matplotlib import font_manager
import unicodedata

import cadquery as cq
import numpy as np
import trimesh

from product_generators.organic_shapes.vessel_engine import OrganicVesselResult

from .body_family_expansion import GeneralBodyFamilyExpander
from .design_pipeline import DoboDesignPipeline


PROFILED_CAD_ADAPTER_VERSION = "PCAD.7-smooth-high-budget"
_PROFILED_ROUTE = "analytic_cad_profiled_revolution"
_PROFILE_SAMPLES_PER_SPAN = 18
_STL_TOLERANCE_MM = 0.015
_STL_ANGULAR_TOLERANCE_RAD = 0.035
_PROFILE_VERTEX_BUDGET = 240_000
_PREVIOUS_GENERATE = None
_PREVIOUS_EXPAND = None


PROFILE_CORE_VARIANTS = (
    "amphora_tapered", "urn_bellied", "barrel", "narrow_neck",
    "flared_rim", "inverted_taper", "hourglass", "tall_taper",
    "oval_tall", "pedestal_urn",
)


PROFILE_CATALOG: dict[str, tuple[tuple[float, float], ...]] = {
    "amphora_tapered": ((0.00,0.50),(0.10,0.62),(0.40,0.90),(0.72,0.78),(0.88,0.45),(1.00,0.52)),
    "urn_bellied": ((0.00,0.58),(0.08,0.68),(0.35,1.00),(0.70,0.88),(0.88,0.55),(1.00,0.62)),
    "barrel": ((0.00,0.75),(0.15,0.90),(0.50,1.00),(0.85,0.90),(1.00,0.76)),
    "narrow_neck": ((0.00,0.58),(0.12,0.70),(0.55,1.00),(0.82,0.72),(0.92,0.42),(1.00,0.45)),
    "flared_rim": ((0.00,0.62),(0.15,0.76),(0.65,0.90),(0.88,0.62),(0.96,0.66),(1.00,0.90)),
    "inverted_taper": ((0.00,0.58),(0.10,0.60),(0.25,0.65),(0.45,0.72),(0.65,0.80),(0.85,0.89),(1.00,0.96)),
    "hourglass": ((0.00,0.86),(0.08,0.83),(0.20,0.74),(0.35,0.60),(0.50,0.48),(0.65,0.60),(0.80,0.76),(0.92,0.88),(1.00,0.92)),
    "tall_taper": ((0.00,0.45),(0.10,0.50),(0.85,0.72),(1.00,0.75)),
    "oval_tall": ((0.00,0.55),(0.12,0.70),(0.50,1.00),(0.88,0.72),(1.00,0.62)),
    "pedestal_urn": ((0.00,0.40),(0.08,0.55),(0.20,0.45),(0.45,0.70),(0.78,0.58),(0.92,0.52),(1.00,0.82)),
    "bell_vase": ((0.00,0.50),(0.12,0.58),(0.55,0.72),(0.82,0.88),(1.00,0.98)),
    "chalice": ((0.00,0.42),(0.10,0.50),(0.22,0.38),(0.48,0.48),(0.72,0.86),(0.92,0.95),(1.00,0.92)),
    "tulip": ((0.00,0.55),(0.08,0.60),(0.20,0.66),(0.35,0.73),(0.50,0.82),(0.68,0.92),(0.84,1.00),(0.94,0.98),(1.00,0.94)),
    "pear": ((0.00,0.48),(0.12,0.62),(0.40,0.95),(0.62,1.00),(0.82,0.75),(1.00,0.58)),
    "teardrop": ((0.00,0.45),(0.08,0.56),(0.20,0.76),(0.35,0.94),(0.50,1.00),(0.65,0.93),(0.80,0.74),(0.92,0.52),(1.00,0.46)),
    "bulb": ((0.00,0.50),(0.10,0.65),(0.35,1.00),(0.62,0.95),(0.82,0.70),(1.00,0.62)),
    "capsule": ((0.00,0.68),(0.07,0.75),(0.16,0.84),(0.30,0.90),(0.70,0.90),(0.84,0.84),(0.94,0.75),(1.00,0.68)),
    "wide_bowl": ((0.00,0.72),(0.08,0.80),(0.20,0.90),(0.40,0.98),(0.65,1.00),(0.82,0.98),(1.00,0.94)),
    "goblet": ((0.00,0.42),(0.10,0.52),(0.24,0.40),(0.40,0.46),(0.62,0.75),(0.85,0.96),(1.00,0.92)),
    "bottle": ((0.00,0.58),(0.10,0.65),(0.45,0.82),(0.70,0.78),(0.82,0.58),(0.92,0.42),(1.00,0.45)),
    "shoulder_jar": ((0.00,0.62),(0.10,0.70),(0.45,0.90),(0.68,1.00),(0.82,0.82),(0.92,0.62),(1.00,0.66)),
    "double_bulb": ((0.00,0.55),(0.08,0.65),(0.18,0.82),(0.30,0.90),(0.42,0.72),(0.50,0.62),(0.58,0.70),(0.68,0.92),(0.78,0.96),(0.88,0.75),(0.95,0.60),(1.00,0.62)),
    "trumpet": ((0.00,0.52),(0.10,0.58),(0.55,0.62),(0.75,0.72),(0.90,0.90),(1.00,1.00)),
    "s_curve": ((0.00,0.60),(0.10,0.68),(0.20,0.80),(0.32,0.86),(0.45,0.72),(0.55,0.60),(0.65,0.64),(0.75,0.76),(0.86,0.90),(0.95,0.86),(1.00,0.80)),
    "footed_bowl": ((0.00,0.38),(0.05,0.45),(0.10,0.58),(0.16,0.50),(0.23,0.46),(0.32,0.56),(0.45,0.72),(0.60,0.88),(0.75,0.98),(0.90,1.00),(1.00,0.92)),
    "drum": ((0.00,0.78),(0.08,0.82),(0.35,0.90),(0.65,0.90),(0.92,0.82),(1.00,0.78)),
    "cone_bell": ((0.00,0.52),(0.08,0.55),(0.20,0.62),(0.40,0.72),(0.60,0.82),(0.80,0.93),(1.00,1.00)),
    "lantern": ((0.00,0.58),(0.06,0.70),(0.12,0.78),(0.22,0.88),(0.32,0.95),(0.42,0.88),(0.50,0.78),(0.58,0.84),(0.68,0.97),(0.78,0.92),(0.88,0.78),(0.96,0.70),(1.00,0.68)),
    "spindle": ((0.00,0.48),(0.10,0.56),(0.40,0.78),(0.55,0.95),(0.70,0.78),(0.90,0.56),(1.00,0.50)),
    "low_urn": ((0.00,0.70),(0.05,0.76),(0.15,0.88),(0.30,0.97),(0.50,1.00),(0.70,0.96),(0.85,0.88),(1.00,0.80)),
}


PROFILE_LABELS: dict[str, str] = {
    "amphora_tapered":"anfora ahusada","urn_bellied":"urna globular","barrel":"barril",
    "narrow_neck":"cuello estrecho","flared_rim":"borde ensanchado","inverted_taper":"tronco invertido",
    "hourglass":"reloj de arena","tall_taper":"ahusada alta","oval_tall":"ovoide alta","pedestal_urn":"urna pedestal",
    "bell_vase":"vaso campana","chalice":"caliz","tulip":"tulipan","pear":"pera","teardrop":"gota",
    "bulb":"bulbosa","capsule":"capsula","wide_bowl":"cuenco ancho","goblet":"copa alta","bottle":"botella",
    "shoulder_jar":"jarra de hombros","double_bulb":"doble bulbo","trumpet":"trompeta","s_curve":"curva s",
    "footed_bowl":"cuenco pedestal","drum":"tambor","cone_bell":"cono campana","lantern":"farol","spindle":"huso","low_urn":"urna baja",
}


PROFILE_DEFAULT_DIMENSIONS: dict[str, tuple[float, float]] = {
    **{variant:(120.0,120.0) for variant in PROFILE_CORE_VARIANTS},
    "bell_vase":(130.0,120.0),"chalice":(140.0,120.0),"tulip":(125.0,120.0),"pear":(130.0,125.0),
    "teardrop":(140.0,118.0),"bulb":(120.0,130.0),"capsule":(145.0,110.0),"wide_bowl":(90.0,145.0),
    "goblet":(145.0,115.0),"bottle":(155.0,105.0),"shoulder_jar":(130.0,125.0),"double_bulb":(145.0,115.0),
    "trumpet":(140.0,120.0),"s_curve":(135.0,120.0),"footed_bowl":(110.0,135.0),"drum":(105.0,130.0),
    "cone_bell":(125.0,125.0),"lantern":(135.0,120.0),"spindle":(150.0,110.0),"low_urn":(95.0,140.0),
}


PROFILE_ALIASES: dict[str, str] = {
    **{variant: variant for variant in PROFILE_CATALOG},
    **{label.replace(" ","_"): variant for variant,label in PROFILE_LABELS.items()},
    "amphora":"amphora_tapered","anfora":"amphora_tapered","urn":"urn_bellied","urna":"urn_bellied",
    "bell":"bell_vase","campana":"bell_vase","copa":"goblet","jarra":"shoulder_jar","gota_agua":"teardrop",
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


_PROFILE_FONT_STYLES: dict[str, dict[str, str]] = {
    "font_clean": {
        "family": "DejaVu Sans",
        "weight": "normal",
        "style": "normal",
        "label": "Limpia",
    },
    "font_strong": {
        "family": "DejaVu Sans",
        "weight": "bold",
        "style": "normal",
        "label": "Fuerte",
    },
    "font_editorial": {
        "family": "DejaVu Serif",
        "weight": "bold",
        "style": "normal",
        "label": "Editorial",
    },
    "font_classic": {
        "family": "DejaVu Serif",
        "weight": "normal",
        "style": "italic",
        "label": "Clásica",
    },
    "font_tech": {
        "family": "DejaVu Sans Mono",
        "weight": "bold",
        "style": "normal",
        "label": "Técnica",
    },
    "font_display": {
        "family": "STIXGeneral",
        "weight": "bold",
        "style": "normal",
        "label": "Display",
    },
    "font_elegant": {
        "family": "STIXGeneral",
        "weight": "normal",
        "style": "italic",
        "label": "Elegante",
    },
}


def _resolved_font_contract(style_id: str) -> dict[str, str]:
    contract = _PROFILE_FONT_STYLES[style_id]
    properties = font_manager.FontProperties(
        family=contract["family"],
        weight=contract["weight"],
        style=contract["style"],
    )
    font_path = font_manager.findfont(properties, fallback_to_default=True)
    return {
        "font_style": style_id,
        "font": contract["family"],
        "kind": "regular",
        "font_path": str(font_path),
        "font_weight": contract["weight"],
        "font_slant": contract["style"],
        "font_label": contract["label"],
    }


def _profile_text_style(program) -> dict[str, str]:
    tags = {_plain(tag) for tag in program.body.style_tags}
    selected = "font_strong"
    for tag in _PROFILE_FONT_STYLES:
        if tag in tags:
            selected = tag
            break
    resolved = _resolved_font_contract(selected)
    resolved["layout"] = "wrap" if "text_layout_wrap" in tags else "front"
    resolved["wrap_target_fraction"] = "0.99"
    return resolved


def _best_profile_text_zone(
    profile: tuple[tuple[float, float], ...],
    *,
    zone_id: str,
    low: float,
    high: float,
    preferred: float,
) -> dict[str, Any]:
    dense = _smooth_profile(profile)
    best_score = -1.0
    best_z = preferred
    best_radius = _radius_at(dense, preferred)
    best_slope = 0.0
    for index in range(49):
        z = low + index * ((high - low) / 48.0)
        radius = _radius_at(dense, z)
        step = 0.008
        slope = abs(
            _radius_at(dense, min(1.0, z + step))
            - _radius_at(dense, max(0.0, z - step))
        ) / (2.0 * step)
        preferred_bias = 1.0 - 0.16 * min(
            1.0,
            abs(z - preferred) / max(0.05, 0.5 * (high - low)),
        )
        score = radius * preferred_bias / (1.0 + 0.60 * slope)
        if score > best_score:
            best_score = score
            best_z = z
            best_radius = radius
            best_slope = slope
    return {
        "id": zone_id,
        "region": "front",
        "center_z_ratio": round(best_z, 4),
        "local_radius_ratio": round(best_radius, 4),
        "slope_abs": round(best_slope, 4),
        "width_fraction": 0.55,
        "height_fraction": 0.14,
        "emboss_allowed": True,
        "deboss_allowed": True,
    }


def _profile_text_zones(
    profile: tuple[tuple[float, float], ...],
) -> dict[str, dict[str, Any]]:
    return {
        "lower": _best_profile_text_zone(
            profile,
            zone_id="front_lower",
            low=0.20,
            high=0.42,
            preferred=0.31,
        ),
        "center": _best_profile_text_zone(
            profile,
            zone_id="front_primary",
            low=0.36,
            high=0.66,
            preferred=0.52,
        ),
        "upper": _best_profile_text_zone(
            profile,
            zone_id="front_upper",
            low=0.62,
            high=0.82,
            preferred=0.72,
        ),
    }


def _profile_text_zone(
    profile: tuple[tuple[float, float], ...],
) -> dict[str, Any]:
    return _profile_text_zones(profile)["center"]


def _saucer_contract(route: dict[str, Any]) -> dict[str, Any]:
    maximum_radius = 0.5 * float(route["diameter_mm"])
    profile = tuple((float(p[0]),float(p[1])) for p in route["normalized_profile"])
    base_radius = maximum_radius * _radius_at(profile, 0.0)
    drain_radius = 0.5 * float(route["drain_diameter_mm"])
    outer_radius = max(base_radius + 6.0, drain_radius + 12.0)
    wall, floor, wall_height, support_height = 2.0, 1.8, 6.0, 1.2
    support_ring = max(drain_radius+5.0, min(0.55*base_radius, outer_radius-wall-5.0))
    return {
        "outer_radius_mm":round(outer_radius,4),"base_footprint_radius_mm":round(base_radius,4),
        "floor_mm":floor,"wall_mm":wall,"wall_height_mm":wall_height,
        "reservoir_depth_mm":wall_height-floor,"support_height_mm":support_height,
        "support_pad_radius_mm":3.5,"support_ring_radius_mm":round(support_ring,4),
        "drain_clearance_mm":support_height,
        "surface_regions":["saucer_body","saucer_rim","saucer_supports"],
        "color_regions":["saucer_body","saucer_rim","saucer_supports"],
    }


def _profiled_saucer(route: dict[str, Any]) -> cq.Shape:
    contract = route.get("saucer")
    if not isinstance(contract, dict):
        raise RuntimeError("Profiled saucer contract is missing.")
    outer_radius=float(contract["outer_radius_mm"]); wall=float(contract["wall_mm"])
    floor=float(contract["floor_mm"]); wall_height=float(contract["wall_height_mm"])
    support_height=float(contract["support_height_mm"]); pad_radius=float(contract["support_pad_radius_mm"])
    support_ring=float(contract["support_ring_radius_mm"])
    outer=cq.Workplane("XY").circle(outer_radius).extrude(wall_height).val()
    inner=(cq.Workplane("XY").workplane(offset=floor).circle(outer_radius-wall).extrude(wall_height-floor+1.0).val())
    shape=outer.cut(inner).clean()
    for angle_deg in (45.0,135.0,225.0,315.0):
        angle=math.radians(angle_deg); x=support_ring*math.cos(angle); y=support_ring*math.sin(angle)
        pad=(cq.Workplane("XY").workplane(offset=floor-0.20).center(x,y).circle(pad_radius).extrude(support_height+0.20).val())
        shape=shape.fuse(pad,tol=0.005).clean()
    if not shape.isValid() or len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Profiled saucer must be one valid printable solid.")
    return shape


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
    route = {
        "adapter_version": PROFILED_CAD_ADAPTER_VERSION,
        "variant": variant,
        "label": PROFILE_LABELS[variant],
        "diameter_mm": diameter,
        "height_mm": float(program.body.height_mm),
        "wall_mm": float(vessel.get("wall_mm", program.manufacturing.minimum_wall_mm)),
        "bottom_mm": bottom,
        "drain_required": drain_radius > 0.0,
        "drain_diameter_mm": 2.0 * drain_radius,
        "control_profile": [list(point) for point in PROFILE_CATALOG[variant]],
        "normalized_profile": [list(point) for point in _smooth_profile(PROFILE_CATALOG[variant])],
        "profile_samples_per_span": _PROFILE_SAMPLES_PER_SPAN,
        "surface_regions": ["body_main","rim","base","text_zone"],
        "color_regions": ["body_main","rim","base","text"],
    }
    route["text_zones"] = _profile_text_zones(PROFILE_CATALOG[variant])
    route["text_zone"] = route["text_zones"]["center"]
    route["saucer"] = _saucer_contract(route)
    route["text_style"] = _profile_text_style(program)
    motor["_profiled_revolution"] = route
    return result


def _smooth_profile(
    profile: tuple[tuple[float, float], ...],
    *,
    samples_per_span: int = _PROFILE_SAMPLES_PER_SPAN,
) -> tuple[tuple[float, float], ...]:
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
    tessellation_tolerance = _STL_TOLERANCE_MM
    tessellation_angular = _STL_ANGULAR_TOLERANCE_RAD
    cq.exporters.export(
        shape,
        str(stl_path),
        tolerance=tessellation_tolerance,
        angularTolerance=tessellation_angular,
    )
    mesh = _load_mesh(stl_path)

    # Keep the design curve dense. Only the final triangle tessellation is relaxed
    # if an unusually complex profile exceeds the rendering/transport budget.
    if len(mesh.vertices) >= _PROFILE_VERTEX_BUDGET:
        for tolerance, angular in (
            (0.020, 0.045),
            (0.025, 0.055),
            (0.030, 0.065),
            (0.040, 0.080),
            (0.055, 0.110),
        ):
            cq.exporters.export(
                shape,
                str(stl_path),
                tolerance=tolerance,
                angularTolerance=angular,
            )
            mesh = _load_mesh(stl_path)
            tessellation_tolerance = tolerance
            tessellation_angular = angular
            if len(mesh.vertices) < _PROFILE_VERTEX_BUDGET:
                break

    saucer_shape = _profiled_saucer(route)
    saucer_path = output_dir / f"{output['basename']}.saucer.stl"
    cq.exporters.export(
        saucer_shape,
        str(saucer_path),
        tolerance=_STL_TOLERANCE_MM,
        angularTolerance=_STL_ANGULAR_TOLERANCE_RAD,
    )
    saucer_mesh = _load_mesh(saucer_path)
    saucer_components = tuple(saucer_mesh.split(only_watertight=False))
    saucer_contract = dict(route["saucer"])
    motor["_profiled_saucer"] = {
        "adapter_version": PROFILED_CAD_ADAPTER_VERSION,
        "stl_path": str(saucer_path),
        **saucer_contract,
        "watertight": bool(saucer_mesh.is_watertight),
        "winding_consistent": bool(saucer_mesh.is_winding_consistent),
        "component_count": len(saucer_components),
        "vertex_count": int(len(saucer_mesh.vertices)),
        "face_count": int(len(saucer_mesh.faces)),
    }

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
        "text_zone_available": isinstance(route.get("text_zone"), dict)
        and route["text_zone"].get("id") == "front_primary",
        "saucer_generated": saucer_path.is_file(),
        "saucer_watertight": bool(saucer_mesh.is_watertight),
        "saucer_winding_consistent": bool(saucer_mesh.is_winding_consistent),
        "saucer_one_component": len(saucer_components) == 1,
        "saucer_drain_clearance": float(saucer_contract["drain_clearance_mm"]) >= 1.0,
        "mesh_budget_respected": int(len(mesh.vertices)) < _PROFILE_VERTEX_BUDGET,
    }
    motor["_profiled_revolution"]["effective_tessellation"] = {
        "tolerance_mm": tessellation_tolerance,
        "angular_tolerance_rad": tessellation_angular,
        "vertex_count": int(len(mesh.vertices)),
        "vertex_budget": _PROFILE_VERTEX_BUDGET,
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
