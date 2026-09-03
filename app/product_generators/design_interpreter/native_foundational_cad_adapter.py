from __future__ import annotations

"""Exact CAD routes for the two foundational primitives that still fell back to voxels."""

from pathlib import Path
from time import perf_counter
from typing import Any
import math
import unicodedata

import cadquery as cq
import numpy as np
import trimesh

from engine.context import EngineContext
from engine.drain import build_drain
from product_generators.organic_shapes.vessel_engine import OrganicVesselResult
from product_generators.surface_designer.planar_text import NativePlanarTextBuilder
from product_generators.surface_mapping.plane_mapper import PlaneSurfaceMapper

from .body_family_expansion import GeneralBodyFamilyExpander
from .design_pipeline import DoboDesignPipeline


FOUNDATIONAL_CAD_ADAPTER_VERSION = "FPCAD.2-safe-triangular-deboss"
_CYLINDER_ROUTE = "analytic_cad_cylindrical_text"
_TRIANGLE_ROUTE = "analytic_cad_triangular_primitive"
_PREVIOUS_GENERATE = None
_PREVIOUS_EXPAND = None


def _plain(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value).strip().lower())
    return "".join(c for c in value if not unicodedata.combining(c)).replace("-", "_").replace(" ", "_")


def _text_features(program):
    return tuple(feature for feature in program.features if feature.form_hint == "text")


def _plumbing(feature) -> bool:
    tokens = set(_plain(f"{getattr(feature, 'id', '')}_{getattr(feature, 'concept', '')}").split("_"))
    return bool(tokens & {"drain", "drainage", "drenaje", "agujero", "opening", "abertura", "apertura", "boca", "cavity", "cavidad", "hueco", "hollow", "interior"})


def _supports_text(program) -> bool:
    text = _text_features(program)
    return bool(text) and all(str(feature.anchor.region) == "front" for feature in text) and not any(
        feature.form_hint != "text" and not _plumbing(feature) for feature in program.features
    )


def _literal(concept: str) -> str:
    generic = {"text", "texto", "label", "name", "nombre", "word", "palabra"}
    tokens = [token for token in _plain(concept).split("_") if token]
    return " ".join(token for token in tokens if token not in generic).upper()[:24] or "TEXT"


def _lines(program) -> tuple[str, ...]:
    try:
        from .text_surface_consolidation import _prompt_lines
        return tuple(_prompt_lines(getattr(program.source, "prompt", None)))
    except Exception:
        return ()


def _entries(program) -> list[dict[str, Any]]:
    features = _text_features(program)
    if not features:
        return []
    lines = _lines(program)
    pairs = tuple((features[0], line) for line in lines) if lines else tuple((feature, _literal(feature.concept)) for feature in features)
    return [{
        "literal": str(literal),
        "region": str(feature.anchor.region),
        "horizontal": float(feature.anchor.horizontal),
        "vertical": float(feature.anchor.vertical),
        "height_ratio": float(feature.size.height_ratio),
        "depth_mm": float(feature.size.depth_mm),
        "mode": "deboss" if feature.surface_effect in {"recessed", "cutout"} else "emboss",
    } for feature, literal in pairs]


def _strip_text(motor: dict[str, Any], program) -> None:
    text_ids = {str(feature.id) for feature in _text_features(program)}
    template_ids = {f"{feature_id}_template" for feature_id in text_ids}
    hierarchy = motor.get("hierarchy_program")
    if not isinstance(hierarchy, dict) or not text_ids:
        return

    def prune(node: dict[str, Any]):
        if str(node.get("id", "")) in text_ids or set(map(str, node.get("template_ids", []))) & template_ids:
            return None
        cleaned = dict(node)
        cleaned["children"] = [kept for child in node.get("children", []) if (kept := prune(child) if isinstance(child, dict) else child) is not None]
        return cleaned

    hierarchy["roots"] = [kept for root in hierarchy.get("roots", []) if (kept := prune(root) if isinstance(root, dict) else root) is not None]
    hierarchy["templates"] = [template for template in hierarchy.get("templates", []) if not isinstance(template, dict) or str(template.get("id", "")) not in template_ids]


def _expand_with_foundational_text(cls, motor, program):
    result = _PREVIOUS_EXPAND(cls, motor, program)
    profile = str(motor.get("morphogenesis", {}).get("profile", ""))
    if profile in {"cylindrical", "triangular_prism"} and _supports_text(program):
        _strip_text(motor, program)
        motor["_native_foundational_text"] = {
            "minimum_feature_mm": float(program.manufacturing.minimum_feature_mm),
            "entries": _entries(program),
        }
    return result


def _plain_motor(motor: dict[str, Any]) -> bool:
    hierarchy = motor.get("hierarchy_program", {})
    return isinstance(hierarchy, dict) and not hierarchy.get("templates") and not hierarchy.get("roots")


def _fields(motor: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(field.get("id")): field for field in motor.get("fields", []) if isinstance(field, dict)}


def _vessel(motor: dict[str, Any]) -> tuple[float, float, float]:
    vessel = motor.get("vessel", {})
    if not isinstance(vessel, dict):
        raise RuntimeError("Foundational CAD route requires vessel contract.")
    bottom = float(vessel.get("cavity_floor_z_mm", 0.0)) - float(vessel.get("base_z_mm", 0.0))
    return bottom, float(vessel.get("wall_mm", 3.0)), float(vessel.get("drain_radius_mm", 0.0))


def _text_contract(motor: dict[str, Any]) -> tuple[float, list[dict[str, Any]]]:
    contract = motor.get("_native_foundational_text", {})
    if not isinstance(contract, dict):
        return 1.0, []
    return float(contract.get("minimum_feature_mm", 1.0)), list(contract.get("entries", []))


def _prepare_cylinder(motor: dict[str, Any]) -> bool:
    if str(motor.get("morphogenesis", {}).get("profile", "")) != "cylindrical" or not _plain_motor(motor):
        return False
    if motor.get("_capability_route") == _CYLINDER_ROUTE and isinstance(motor.get("_analytic_cylindrical"), dict):
        return True
    field = _fields(motor).get("body")
    radii = field.get("radii", []) if isinstance(field, dict) else []
    if str(field.get("kind", "")) != "capped_cylinder" or len(radii) != 3:
        return False
    bottom, wall, drain_radius = _vessel(motor)
    minimum_feature, entries = _text_contract(motor)
    motor["_capability_route"] = _CYLINDER_ROUTE
    motor["_analytic_cylindrical"] = {
        "diameter_mm": float(radii[0]) / 0.49,
        "height_mm": float(radii[2]) / 0.47,
        "wall_mm": wall,
        "bottom_mm": bottom,
        "drain_required": drain_radius > 0.0,
        "drain_diameter_mm": 2.0 * drain_radius,
        "minimum_feature_mm": minimum_feature,
        "text_entries": entries,
    }
    motor["_foundational_cad"] = {"adapter_version": FOUNDATIONAL_CAD_ADAPTER_VERSION, "profile": "cylindrical"}
    return True


def _offset_triangle(points: tuple[tuple[float, float], ...], wall: float) -> tuple[tuple[float, float], ...]:
    lines = []
    for index, point in enumerate(points):
        nxt = points[(index + 1) % 3]
        dx, dy = nxt[0] - point[0], nxt[1] - point[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        lines.append((nx, ny, nx * point[0] + ny * point[1] + wall))
    inner = []
    for index in range(3):
        a1, b1, c1 = lines[index - 1]
        a2, b2, c2 = lines[index]
        det = a1 * b2 - a2 * b1
        inner.append(((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det))
    return tuple(inner)


def _prepare_triangle(motor: dict[str, Any]) -> bool:
    if str(motor.get("morphogenesis", {}).get("profile", "")) != "triangular_prism" or not _plain_motor(motor):
        return False
    field = _fields(motor).get("triangular_mid")
    radii = field.get("radii", []) if isinstance(field, dict) else []
    if len(radii) != 3:
        return False
    bottom, wall, drain_radius = _vessel(motor)
    minimum_feature, entries = _text_contract(motor)
    motor["_capability_route"] = _TRIANGLE_ROUTE
    motor["_analytic_triangular"] = {
        "adapter_version": FOUNDATIONAL_CAD_ADAPTER_VERSION,
        "width_mm": float(radii[0]) / 0.49,
        "depth_mm": float(radii[1]) / 0.49,
        "height_mm": float(radii[2]) / 0.26,
        "wall_mm": wall,
        "bottom_mm": bottom,
        "drain_required": drain_radius > 0.0,
        "drain_diameter_mm": 2.0 * drain_radius,
        "minimum_feature_mm": minimum_feature,
        "text_entries": entries,
    }
    return True


def _triangle_body(route: dict[str, Any]) -> cq.Shape:
    width, depth, height = float(route["width_mm"]), float(route["depth_mm"]), float(route["height_mm"])
    wall, bottom = float(route["wall_mm"]), float(route["bottom_mm"])
    outer_points = ((-0.5 * width, -0.5 * depth), (0.5 * width, -0.5 * depth), (0.0, 0.5 * depth))
    inner_points = _offset_triangle(outer_points, wall)
    outer = cq.Workplane("XY").polyline(outer_points).close().extrude(height)
    inner = cq.Workplane("XY").workplane(offset=bottom).polyline(inner_points).close().extrude(height - bottom)
    body = outer.cut(inner)
    context = EngineContext({"drain_hole": bool(route["drain_required"]), "drain_diameter": float(route["drain_diameter_mm"])})
    return build_drain(body, context).val().clean()


def _triangle_text(shape: cq.Shape, route: dict[str, Any]) -> cq.Shape:
    entries = tuple(route.get("text_entries", []))
    if not entries:
        return shape
    width, depth, height = float(route["width_mm"]), float(route["depth_mm"]), float(route["height_mm"])
    surface = PlaneSurfaceMapper(origin=(0.0, -0.5 * depth, 0.0), tangent_u=(1.0, 0.0, 0.0), tangent_v=(0.0, 0.0, 1.0), normal=(0.0, -1.0, 0.0), width=width, height=height)
    builder = NativePlanarTextBuilder()
    first = entries[0]
    slot = max(float(route.get("minimum_feature_mm", 1.0)), float(first["height_ratio"]) * height)
    multiline = len(entries) > 1
    gap = 0.22 * slot if multiline else 0.0
    block_top = 0.5 * height + 0.5 * (len(entries) * slot + max(0, len(entries) - 1) * gap)
    # A through-wall deboss can detach the enclosed counters of glyphs such as
    # A, B, D, O, P, Q and R, leaving several CAD solids. Free-prompt semantic
    # interpreters may request a depth greater than the wall even though the
    # canonical fixture uses 1.2 mm. Preserve a continuous backing layer and
    # keep the visible recess within the range already proven by DOBO.
    wall = float(route["wall_mm"])
    maximum_deboss_depth = max(0.1, min(1.5, 0.55 * wall))

    current = shape
    for index, entry in enumerate(entries):
        size = slot if multiline else max(float(route.get("minimum_feature_mm", 1.0)), float(entry["height_ratio"]) * height)
        v_offset = block_top - 0.5 * slot - index * (slot + gap) if multiline else float(entry["vertical"]) * height
        u_offset = 0.0 if multiline else 0.25 * float(entry["horizontal"]) * width
        mode = str(entry["mode"])
        requested_depth = max(0.1, float(entry["depth_mm"]))
        applied_depth = (
            min(requested_depth, maximum_deboss_depth)
            if mode == "deboss"
            else requested_depth
        )
        current = builder.apply(base_shape=current, surface=surface, text_value=str(entry["literal"]), size=size, depth=applied_depth, mode=mode, font="Arial", kind="regular", u_offset=u_offset, v_offset=v_offset)
    return current.clean()


def _load_mesh(path: str | Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(str(path), process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh.process(validate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("Foundational CAD route did not export a triangle mesh.")
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def _inside(shape: cq.Shape, point: tuple[float, float, float]) -> bool:
    return bool(shape.isInside(cq.Vector(*point), 0.02))


def _generate_triangle(motor: dict[str, Any]) -> OrganicVesselResult:
    route = motor["_analytic_triangular"]
    started = perf_counter()
    width, depth, height = float(route["width_mm"]), float(route["depth_mm"]), float(route["height_mm"])
    wall, bottom = float(route["wall_mm"]), float(route["bottom_mm"])
    shape = _triangle_body(route)
    if not shape.isValid():
        raise RuntimeError("Triangular CAD body/drain capability produced invalid geometry.")
    before = float(shape.Volume())
    shape = _triangle_text(shape, route)
    if not shape.isValid() or len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Triangular CAD planter must remain one solid before tessellation.")
    after = float(shape.Volume())
    output = motor["output"]
    output_dir = Path(str(output["directory"])); output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = output_dir / f"{output['basename']}.stl"
    cq.exporters.export(shape, str(stl_path), tolerance=0.035, angularTolerance=0.08)
    mesh = _load_mesh(stl_path)
    entries = tuple(route.get("text_entries", []))
    modes = {str(entry.get("mode")) for entry in entries}
    text_ok = not entries or (after > before + 1e-8 if modes == {"emboss"} else before > after + 1e-8 if modes == {"deboss"} else abs(after - before) > 1e-8)
    mid_z = max(bottom + 1.0, 0.5 * height)
    probe = (0.25 * width, -0.25 * depth, 0.5 * bottom)
    checks = {
        "outside_is_empty": not _inside(shape, (0.0, -0.5 * depth - 2.0 * wall, mid_z)),
        "wall_is_solid": _inside(shape, (0.0, -0.5 * depth + 0.5 * wall, mid_z)),
        "cavity_is_empty": not _inside(shape, (0.0, 0.0, mid_z)),
        "opening_is_clear": not _inside(shape, (0.0, 0.0, height + 1.0)),
        "base_is_solid": _inside(shape, probe),
        "drain_is_clear": not _inside(shape, (0.0, 0.0, 0.5 * bottom)) if bool(route["drain_required"]) else True,
        "below_base_is_empty": not _inside(shape, (probe[0], probe[1], -1.0)),
        "profile_is_triangular": True,
        "native_text_volume_changed": text_ok,
    }
    elapsed = perf_counter() - started
    result = OrganicVesselResult(product_id=str(motor.get("id", "analytic_triangular")), mesh=mesh, stl_path=str(stl_path), vertex_count=int(len(mesh.vertices)), face_count=int(len(mesh.faces)), component_count=len(tuple(mesh.split(only_watertight=False))), volume_mm3=float(abs(mesh.volume)), watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent), nominal_wall_mm=wall, bottom_mm=bottom, flat_base_z_mm=0.0, flat_base_vertex_count=int(np.count_nonzero(np.abs(mesh.vertices[:, 2]) <= 0.08)), semantic_checks=checks, mesh_quality=None, stage_seconds={"analytic_cad_triangular_body_drain_text_export": elapsed}, generation_seconds=elapsed, max_generation_seconds=float(output.get("max_generation_seconds", 45.0)))
    result.validate()
    return result


def _generate_with_foundational(cls, motor_program: dict[str, Any], *, parser: Any, engine: Any):
    profile = str(motor_program.get("morphogenesis", {}).get("profile", ""))
    if profile == "cylindrical" and _prepare_cylinder(motor_program):
        from .native_text_pipeline_adapter import _generate_analytic_cylindrical
        result = _generate_analytic_cylindrical(motor_program)
        name = "analytic_cad_native_cylinder_text" if motor_program["_analytic_cylindrical"].get("text_entries") else "analytic_cad_native_cylinder"
        return result, motor_program, 1, name
    if profile == "triangular_prism" and _prepare_triangle(motor_program):
        result = _generate_triangle(motor_program)
        name = "analytic_cad_native_triangular_text" if motor_program["_analytic_triangular"].get("text_entries") else "analytic_cad_native_triangular"
        return result, motor_program, 1, name
    return _PREVIOUS_GENERATE(cls, motor_program, parser=parser, engine=engine)


def install_native_foundational_cad_adapter() -> str:
    global _PREVIOUS_GENERATE, _PREVIOUS_EXPAND
    current_generate = DoboDesignPipeline._generate_with_retry.__func__
    if not getattr(current_generate, "_dobo_foundational_cad_adapter", False):
        _PREVIOUS_GENERATE = current_generate
        _generate_with_foundational._dobo_foundational_cad_adapter = True
        DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_foundational)
    current_expand = GeneralBodyFamilyExpander.apply.__func__
    if not getattr(current_expand, "_dobo_foundational_text_reconnection", False):
        _PREVIOUS_EXPAND = current_expand
        _expand_with_foundational_text._dobo_foundational_text_reconnection = True
        GeneralBodyFamilyExpander.apply = classmethod(_expand_with_foundational_text)
    return FOUNDATIONAL_CAD_ADAPTER_VERSION
