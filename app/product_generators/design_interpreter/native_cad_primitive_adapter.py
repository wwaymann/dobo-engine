from __future__ import annotations

"""Native CAD routing for angular planter bodies and their planar text.

Cube and rectangular-prism bodies reuse DOBO's historical CadQuery body/drain
capabilities.  Text is applied in CAD through one shared planar-surface builder;
unsupported decorations continue to use the existing volumetric route.
"""

from pathlib import Path
from time import perf_counter
from typing import Any
import unicodedata

import cadquery as cq
import numpy as np
import trimesh

from engine.body import build_body
from engine.context import EngineContext
from engine.drain import build_drain
from product_generators.organic_shapes.vessel_engine import OrganicVesselResult
from product_generators.surface_designer.planar_text import NativePlanarTextBuilder
from product_generators.surface_mapping.plane_mapper import PlaneSurfaceMapper

from .design_pipeline import DoboDesignPipeline
from .semantic_contract import DesignSemanticProgram


NATIVE_CAD_PRIMITIVE_ADAPTER_VERSION = "NCAP.3-planar-native-text"
_ANALYTIC_ANGULAR_ROUTE = "analytic_cad_angular_primitive"
_PREVIOUS_GENERATE_WITH_RETRY = None

_CUBOID_ALIASES = {"cuboid", "cube", "cubic", "architectural_cube", "boxy"}
_RECTANGULAR_ALIASES = {
    "rectangular", "rectangular_prism", "elongated_planter", "oblong"
}


def _plain(value: object) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value).strip().lower())
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("-", "_").replace(" ", "_")


def _angular_profile_from_program(program: DesignSemanticProgram) -> str | None:
    values = {_plain(program.body.family), *(_plain(tag) for tag in program.body.style_tags)}
    if values & _CUBOID_ALIASES:
        return "cuboid"
    if values & _RECTANGULAR_ALIASES:
        return "rectangular_prism"
    return None


def _literal_from_concept(concept: str) -> str:
    tokens = [token for token in _plain(concept).split("_") if token]
    generic = {"text", "texto", "label", "name", "nombre", "word", "palabra"}
    literal = [token for token in tokens if token not in generic]
    return " ".join(literal or tokens).upper()[:24]


def _plumbing_feature(feature) -> bool:
    value = f"{getattr(feature, 'id', '')}_{getattr(feature, 'concept', '')}"
    tokens = set(_plain(value).split("_"))
    return bool(tokens & {
        "drain", "drainage", "drenaje", "agujero",
        "opening", "abertura", "apertura", "boca",
        "cavity", "cavidad", "hueco", "hollow", "interior",
    })


def uses_native_angular_text(program: DesignSemanticProgram) -> bool:
    if _angular_profile_from_program(program) is None:
        return False
    text_features = tuple(feature for feature in program.features if feature.form_hint == "text")
    if not text_features:
        return False
    if any(str(feature.anchor.region) != "front" for feature in text_features):
        return False
    unsupported = tuple(
        feature
        for feature in program.features
        if feature.form_hint != "text" and not _plumbing_feature(feature)
    )
    return not unsupported


def prepare_native_angular_text_contract(
    motor: dict[str, Any],
    program: DesignSemanticProgram,
) -> bool:
    if not uses_native_angular_text(program):
        return False
    entries = []
    for feature in program.features:
        if feature.form_hint != "text":
            continue
        entries.append({
            "literal": _literal_from_concept(feature.concept),
            "region": str(feature.anchor.region),
            "horizontal": float(feature.anchor.horizontal),
            "vertical": float(feature.anchor.vertical),
            "height_ratio": float(feature.size.height_ratio),
            "depth_mm": float(feature.size.depth_mm),
            "mode": "deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss",
        })
    motor["_native_angular_text"] = {
        "minimum_feature_mm": float(program.manufacturing.minimum_feature_mm),
        "entries": entries,
    }
    return True


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
        return (
            float(radii[0]) / 0.49,
            float(radii[1]) / 0.49,
            float(radii[2]) / 0.29,
        )

    if profile == "rectangular_prism":
        field = fields.get("rectangular_mid")
        if not isinstance(field, dict):
            raise RuntimeError("Rectangular CAD route is missing mid field.")
        radii = field.get("radii", [])
        if len(radii) != 3:
            raise RuntimeError("Rectangular CAD route has invalid mid radii.")
        return (
            float(radii[0]) / 0.49,
            float(radii[1]) / 0.48,
            float(radii[2]) / 0.29,
        )

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
    text_contract = motor.get("_native_angular_text", {})

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
        "minimum_feature_mm": float(text_contract.get("minimum_feature_mm", 1.0)),
        "text_entries": list(text_contract.get("entries", [])),
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


def _apply_planar_text(shape: cq.Shape, route: dict[str, Any]) -> cq.Shape:
    entries = tuple(route.get("text_entries", []))
    if not entries:
        return shape

    width = float(route["width_mm"])
    depth = float(route["depth_mm"])
    height = float(route["height_mm"])
    minimum_feature = float(route.get("minimum_feature_mm", 1.0))
    surface = PlaneSurfaceMapper(
        origin=(0.0, -0.5 * depth, 0.0),
        tangent_u=(1.0, 0.0, 0.0),
        tangent_v=(0.0, 0.0, 1.0),
        normal=(0.0, -1.0, 0.0),
        width=width,
        height=height,
    )
    builder = NativePlanarTextBuilder()

    gap_ratio = 0.22
    first = entries[0]
    multiline = len(entries) > 1
    slot_height = max(minimum_feature, float(first["height_ratio"]) * height)
    gap = gap_ratio * slot_height if multiline else 0.0
    total_height = len(entries) * slot_height + max(0, len(entries) - 1) * gap
    block_center = 0.5 * height if multiline else float(first["vertical"]) * height
    block_top = block_center + 0.5 * total_height

    current = shape
    for index, entry in enumerate(entries):
        if multiline:
            v_offset = block_top - 0.5 * slot_height - index * (slot_height + gap)
            size = slot_height
            u_offset = 0.0
        else:
            v_offset = float(entry["vertical"]) * height
            size = max(minimum_feature, float(entry["height_ratio"]) * height)
            u_offset = 0.25 * float(entry["horizontal"]) * width
        current = builder.apply(
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
    return current.clean()


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

    base_volume = float(shape.Volume())
    shape = _apply_planar_text(shape, route).clean()
    if not shape.isValid() or len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Native CAD angular planter must remain one solid before tessellation.")
    final_volume = float(shape.Volume())

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
        base_probe_x = 0.5 * (
            drain_radius + max(drain_radius + 0.5, half_width - wall)
        )
    entries = tuple(route.get("text_entries", []))
    text_volume_changed = True
    if entries:
        modes = {str(entry.get("mode")) for entry in entries}
        if modes == {"emboss"}:
            text_volume_changed = final_volume > base_volume + 1e-8
        elif modes == {"deboss"}:
            text_volume_changed = final_volume < base_volume - 1e-8
        else:
            text_volume_changed = abs(final_volume - base_volume) > 1e-8

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
        "native_text_volume_changed": text_volume_changed,
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
        stage_seconds={"analytic_cad_angular_body_drain_text_export": elapsed},
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
        profile = (
            "analytic_cad_native_primitive_text"
            if motor_program.get("_analytic_angular", {}).get("text_entries")
            else "analytic_cad_native_primitive"
        )
        return native_result, motor_program, 1, profile
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
