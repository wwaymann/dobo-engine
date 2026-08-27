from __future__ import annotations

"""Canonical reconnection of semantic text into the DOBO structural engine.

Text geometry is evaluated against the resolved receiving surface instead of a
guessed local curvature, and glyphs reuse CadQuery text contours rather than a
coarse segment-display alphabet.
"""

from copy import deepcopy
from functools import lru_cache
import unicodedata

import cadquery as cq
import numpy as np

from .body_family_expansion import GeneralBodyFamilyExpander
from .design_pipeline import DoboDesignPipeline
from .semantic_compiler import SemanticToMotorCompiler
from product_generators.organic_shapes.feature_program_engine import (
    FeatureProgramVesselEngine,
)
from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)


CORE_CAPABILITY_RECONNECTION_VERSION = "C0R.4-resolved-surface-glyphs"
_TEXT_GENERATION_BUDGET_SECONDS = 120.0
_TEXT_TEMPLATES: dict[str, str] = {}
_TEXT_WRAP_RADIUS: dict[str, float] = {}
_INSTALLED = False

_ORIGINAL_FIELD = FeatureProgramVesselEngine._feature_field
_ORIGINAL_PLACED_FIELD = HierarchicalFeatureVesselEngine._placed_field.__func__
_ORIGINAL_APPLY = GeneralBodyFamilyExpander.apply.__func__
_ORIGINAL_COMPILE_FEATURE = SemanticToMotorCompiler._compile_feature.__func__
_ORIGINAL_GENERATE_WITH_RETRY = DoboDesignPipeline._generate_with_retry.__func__


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )


def _literal_from_concept(concept: str) -> str:
    tokens = [token for token in _plain(concept).split("_") if token]
    generic = {
        "text",
        "texto",
        "label",
        "name",
        "nombre",
        "word",
        "palabra",
    }
    literal = [token for token in tokens if token not in generic]
    return " ".join(literal or tokens).upper()[:24]


def _compile_feature_with_text(cls, feature, **kwargs):
    template, transform = _ORIGINAL_COMPILE_FEATURE(cls, feature, **kwargs)
    if feature.form_hint != "text":
        return template, transform

    literal = _literal_from_concept(feature.concept)
    template["semantic_kind"] = "text_glyph_contour"
    template["text_literal"] = literal

    if template.get("kind") == "rounded_box" and template.get("half_sizes"):
        half_sizes = [float(value) for value in template["half_sizes"]]
        minimum_feature = float(kwargs.get("minimum_feature_mm", 0.0))
        minimum_relief = float(kwargs.get("minimum_relief_depth_mm", 0.0))
        maximum_relief = float(
            kwargs.get("maximum_relief_depth_mm", half_sizes[1])
        )
        safe_half_depth = max(
            half_sizes[1],
            0.65 * minimum_feature,
            1.01 * minimum_relief,
        )
        half_sizes[1] = min(safe_half_depth, maximum_relief)
        template["half_sizes"] = half_sizes
        if template.get("round_mm") is not None:
            template["round_mm"] = min(
                float(template["round_mm"]),
                0.90 * min(half_sizes),
            )

    return template, transform


def _body_cylinder_radius(motor_program) -> float | None:
    for field in motor_program.get("fields", []):
        if not isinstance(field, dict):
            continue
        if str(field.get("id")) != "body":
            continue
        if str(field.get("kind")) != "capped_cylinder":
            continue
        radii = field.get("radii")
        if isinstance(radii, list) and radii:
            radius = float(radii[0])
            if radius > 0.0:
                return radius
    return None


def _find_node(nodes, feature_id: str):
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("id")) == feature_id:
            return node
        found = _find_node(node.get("children", []), feature_id)
        if found is not None:
            return found
    return None


def _apply_with_text_contract(cls, motor_program, program):
    _TEXT_TEMPLATES.clear()
    _TEXT_WRAP_RADIUS.clear()

    result = _ORIGINAL_APPLY(cls, motor_program, program)
    profile = cls.requested_profile(program)
    wrap_radius = (
        _body_cylinder_radius(motor_program)
        if profile == "cylindrical"
        else None
    )
    text_features = tuple(
        feature for feature in program.features if feature.form_hint == "text"
    )

    if text_features:
        grid = motor_program.get("grid", {})
        vessel = motor_program.get("vessel", {})
        if isinstance(grid, dict) and isinstance(vessel, dict):
            current_voxel = float(grid.get("voxel_mm", 1.0))
            wall_mm = float(vessel.get("wall_mm", 0.0))
            bottom_mm = float(vessel.get("cavity_floor_z_mm", 0.0)) - float(
                vessel.get("base_z_mm", 0.0)
            )
            positive_limits = [
                value for value in (wall_mm, bottom_mm) if value > 0.0
            ]
            if positive_limits:
                grid["voxel_mm"] = min(
                    current_voxel,
                    0.99 * min(positive_limits) / 3.0,
                )

    hierarchy = motor_program.get("hierarchy_program", {})
    template_items = hierarchy.get("templates", []) if isinstance(hierarchy, dict) else []
    templates = {
        str(item.get("id")): item
        for item in template_items
        if isinstance(item, dict)
    }

    for feature in text_features:
        template_id = f"{feature.id}_template"
        literal = _literal_from_concept(feature.concept)
        _TEXT_TEMPLATES[template_id] = literal
        if wrap_radius is not None:
            _TEXT_WRAP_RADIUS[template_id] = wrap_radius

        template = templates.get(template_id)
        if template is not None:
            template["semantic_kind"] = "text_glyph_contour"
            template["text_literal"] = literal
            template["text_wrap_radius_mm"] = wrap_radius

        if isinstance(hierarchy, dict):
            node = _find_node(hierarchy.get("roots", []), feature.id)
            if node is not None:
                node["template_ids"] = [template_id]

    return result


def _bottom_faces(shape: cq.Shape) -> tuple[cq.Face, ...]:
    z_min = float(shape.BoundingBox().zmin)
    tolerance = 1e-6
    return tuple(
        face
        for face in shape.Faces()
        if abs(float(face.BoundingBox().zmax) - float(face.BoundingBox().zmin))
        <= tolerance
        and abs(float(face.BoundingBox().zmin) - z_min) <= tolerance
    )


@lru_cache(maxsize=64)
def _glyph_triangles(text: str):
    last_error: Exception | None = None
    shape = None
    for font in ("Arial", "DejaVu Sans", "Liberation Sans"):
        try:
            candidate = cq.Compound.makeText(
                text,
                1.0,
                1.0,
                font=font,
                kind="regular",
                halign="left",
                valign="bottom",
            )
            if isinstance(candidate, cq.Shape) and candidate.isValid():
                shape = candidate
                break
        except Exception as error:
            last_error = error

    if shape is None:
        raise RuntimeError("Could not generate a real text contour.") from last_error

    triangle_rows: list[tuple[tuple[float, float], ...]] = []
    points: list[tuple[float, float]] = []
    for face in _bottom_faces(shape):
        vertices, triangles = face.tessellate(0.035, 0.08)
        for triangle in triangles:
            row = tuple(
                (float(vertices[int(index)].x), float(vertices[int(index)].y))
                for index in triangle
            )
            triangle_rows.append(row)
            points.extend(row)

    if not triangle_rows or not points:
        raise RuntimeError("Text contour tessellation produced no triangles.")

    triangles_array = np.asarray(triangle_rows, dtype=np.float64)
    points_array = np.asarray(points, dtype=np.float64)
    minimum = points_array.min(axis=0)
    maximum = points_array.max(axis=0)
    size = maximum - minimum
    if min(float(size[0]), float(size[1])) <= 0.0:
        raise RuntimeError("Text contour bounds are invalid.")
    center = 0.5 * (minimum + maximum)
    triangles_array -= center[None, None, :]
    return triangles_array, float(size[0]), float(size[1])


def _segment_distance_2d(px, pz, ax, az, bx, bz):
    dx = bx - ax
    dz = bz - az
    denominator = max(dx * dx + dz * dz, 1e-12)
    t = np.clip(((px - ax) * dx + (pz - az) * dz) / denominator, 0.0, 1.0)
    qx = ax + t * dx
    qz = az + t * dz
    return np.sqrt((px - qx) ** 2 + (pz - qz) ** 2)


def _triangle_distance_2d(px, pz, triangle):
    (ax, az), (bx, bz), (cx, cz) = triangle
    d0 = _segment_distance_2d(px, pz, ax, az, bx, bz)
    d1 = _segment_distance_2d(px, pz, bx, bz, cx, cz)
    d2 = _segment_distance_2d(px, pz, cx, cz, ax, az)
    distance = np.minimum(d0, np.minimum(d1, d2))

    c0 = (bx - ax) * (pz - az) - (bz - az) * (px - ax)
    c1 = (cx - bx) * (pz - bz) - (cz - bz) * (px - bx)
    c2 = (ax - cx) * (pz - cz) - (az - cz) * (px - cx)
    inside = ((c0 >= 0.0) & (c1 >= 0.0) & (c2 >= 0.0)) | (
        (c0 <= 0.0) & (c1 <= 0.0) & (c2 <= 0.0)
    )
    return np.where(inside, -distance, distance)


def _extruded_2d_distance(planar_distance, depth_coordinate, half_depth):
    slab = np.abs(depth_coordinate) - half_depth
    outside = np.sqrt(
        np.maximum(planar_distance, 0.0) ** 2
        + np.maximum(slab, 0.0) ** 2
    )
    inside = np.minimum(np.maximum(planar_distance, slab), 0.0)
    return outside + inside


def _font_text_field(feature, text: str, u, depth_coordinate, v):
    half_sizes = feature.half_sizes
    if half_sizes is None:
        return _ORIGINAL_FIELD(feature, u, depth_coordinate, v)

    total_width = 2.0 * float(half_sizes[0])
    total_height = 2.0 * float(half_sizes[2])
    half_depth = float(half_sizes[1])
    triangles, natural_width, natural_height = _glyph_triangles(text or "TEXT")
    scale = min(total_width / natural_width, total_height / natural_height)
    scaled = triangles * scale

    planar = None
    for triangle in scaled:
        distance = _triangle_distance_2d(u, v, triangle)
        planar = distance if planar is None else np.minimum(planar, distance)

    if planar is None:
        return _ORIGINAL_FIELD(feature, u, depth_coordinate, v)
    return _extruded_2d_distance(planar, depth_coordinate, half_depth)


def _feature_field(feature, x, y, z):
    text = _TEXT_TEMPLATES.get(feature.id)
    if text:
        center = feature.center or (0.0, 0.0, 0.0)
        return _font_text_field(
            feature,
            text,
            x - float(center[0]),
            y - float(center[1]),
            z - float(center[2]),
        )
    return _ORIGINAL_FIELD(feature, x, y, z)


def _placed_field_with_resolved_surface(cls, placement, x, y, z):
    text = _TEXT_TEMPLATES.get(placement.feature.id)
    radius = _TEXT_WRAP_RADIUS.get(placement.feature.id)
    if not text or radius is None or radius <= 0.0:
        return _ORIGINAL_PLACED_FIELD(cls, placement, x, y, z)

    matrix = np.asarray(placement.matrix, dtype=np.float64)
    origin = matrix[:3, 3]
    tangent_column = matrix[:3, 0]
    inward_column = matrix[:3, 1]
    vertical_column = matrix[:3, 2]

    scale_u = max(float(np.linalg.norm(tangent_column)), 1e-12)
    scale_n = max(float(np.linalg.norm(inward_column)), 1e-12)
    scale_v = max(float(np.linalg.norm(vertical_column)), 1e-12)
    tangent = tangent_column / scale_u
    outward = -inward_column / scale_n
    vertical = vertical_column / scale_v

    center_x = float(origin[0] - outward[0] * radius)
    center_y = float(origin[1] - outward[1] * radius)
    dx = x - center_x
    dy = y - center_y
    radial_distance = np.sqrt(dx * dx + dy * dy)
    normal_projection = dx * outward[0] + dy * outward[1]
    tangent_projection = dx * tangent[0] + dy * tangent[1]
    angle = np.arctan2(tangent_projection, normal_projection)
    u = radius * angle / scale_u
    depth_coordinate = (radial_distance - radius) / scale_n

    world_dx = x - float(origin[0])
    world_dy = y - float(origin[1])
    world_dz = z - float(origin[2])
    v = (
        world_dx * vertical[0]
        + world_dy * vertical[1]
        + world_dz * vertical[2]
    ) / scale_v

    return (
        _font_text_field(
            placement.feature,
            text,
            u,
            depth_coordinate,
            v,
        )
        * placement.distance_scale
    )


def _generate_with_text_budget(cls, motor_program, *, parser, engine):
    candidate = motor_program
    if _TEXT_TEMPLATES:
        candidate = deepcopy(motor_program)
        output = candidate.setdefault("output", {})
        output["max_generation_seconds"] = max(
            float(output.get("max_generation_seconds", 0.0)),
            _TEXT_GENERATION_BUDGET_SECONDS,
        )
    return _ORIGINAL_GENERATE_WITH_RETRY(
        cls,
        candidate,
        parser=parser,
        engine=engine,
    )


def install_core_capability_reconnection() -> str:
    global _INSTALLED
    if _INSTALLED:
        return CORE_CAPABILITY_RECONNECTION_VERSION

    GeneralBodyFamilyExpander.apply = classmethod(_apply_with_text_contract)
    SemanticToMotorCompiler._compile_feature = classmethod(_compile_feature_with_text)
    FeatureProgramVesselEngine._feature_field = staticmethod(_feature_field)
    HierarchicalFeatureVesselEngine._placed_field = classmethod(
        _placed_field_with_resolved_surface
    )
    DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_text_budget)
    _INSTALLED = True
    return CORE_CAPABILITY_RECONNECTION_VERSION
