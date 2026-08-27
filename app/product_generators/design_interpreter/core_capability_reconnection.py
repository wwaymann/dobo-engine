from __future__ import annotations

"""Canonical reconnection of semantic text into the DOBO structural engine.

Text geometry is evaluated against the resolved receiving surface instead of a
guessed local curvature. Real CadQuery glyph contours are converted once into a
cached 2D signed-distance field, so the structural voxel field can evaluate text
without repeating expensive per-triangle geometry work at every sample point.
"""

from copy import deepcopy
from functools import lru_cache
import math
import unicodedata

import cadquery as cq
import numpy as np
from scipy.ndimage import distance_transform_edt

from .body_family_expansion import GeneralBodyFamilyExpander
from .design_pipeline import DoboDesignPipeline
from .semantic_compiler import SemanticToMotorCompiler
from product_generators.organic_shapes.feature_program_engine import (
    FeatureProgramVesselEngine,
)
from product_generators.organic_shapes.hierarchy_engine import (
    HierarchicalFeatureVesselEngine,
)


CORE_CAPABILITY_RECONNECTION_VERSION = "C0R.5-resolved-surface-glyph-sdf"
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
    template_items = (
        hierarchy.get("templates", []) if isinstance(hierarchy, dict) else []
    )
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
                # Text must contribute exactly its real glyph geometry. Generic
                # connector/flare helper templates are not allowed to survive
                # as visible plaques around the opening or side wall.
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
    # The contour itself remains real OCC typography. Tessellation only feeds a
    # one-time 2D SDF cache, so this can stay reasonably fine without exploding
    # the 3D field evaluation cost.
    for face in _bottom_faces(shape):
        vertices, triangles = face.tessellate(0.045, 0.10)
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


def _triangle_mask(xx, zz, triangle):
    (ax, az), (bx, bz), (cx, cz) = triangle
    c0 = (bx - ax) * (zz - az) - (bz - az) * (xx - ax)
    c1 = (cx - bx) * (zz - bz) - (cz - bz) * (xx - bx)
    c2 = (ax - cx) * (zz - cz) - (az - cz) * (xx - cx)
    return ((c0 >= 0.0) & (c1 >= 0.0) & (c2 >= 0.0)) | (
        (c0 <= 0.0) & (c1 <= 0.0) & (c2 <= 0.0)
    )


@lru_cache(maxsize=64)
def _glyph_sdf(text: str):
    triangles, natural_width, natural_height = _glyph_triangles(text or "TEXT")

    # 256 pixels through the glyph height is enough to preserve curved letter
    # contours well beyond the final vessel voxel resolution. Width follows the
    # real text aspect ratio and is capped only to avoid pathological strings.
    height_px = 256
    width_px = int(
        np.clip(
            math.ceil(height_px * natural_width / natural_height),
            128,
            2048,
        )
    )
    margin = 0.08 * max(natural_width, natural_height)
    x_min = -0.5 * natural_width - margin
    x_max = 0.5 * natural_width + margin
    z_min = -0.5 * natural_height - margin
    z_max = 0.5 * natural_height + margin
    xs = np.linspace(x_min, x_max, width_px, dtype=np.float64)
    zs = np.linspace(z_min, z_max, height_px, dtype=np.float64)
    occupancy = np.zeros((height_px, width_px), dtype=bool)

    dx = (x_max - x_min) / max(width_px - 1, 1)
    dz = (z_max - z_min) / max(height_px - 1, 1)

    for triangle in triangles:
        tx_min = float(np.min(triangle[:, 0]))
        tx_max = float(np.max(triangle[:, 0]))
        tz_min = float(np.min(triangle[:, 1]))
        tz_max = float(np.max(triangle[:, 1]))
        ix0 = max(0, int(math.floor((tx_min - x_min) / dx)) - 1)
        ix1 = min(width_px, int(math.ceil((tx_max - x_min) / dx)) + 2)
        iz0 = max(0, int(math.floor((tz_min - z_min) / dz)) - 1)
        iz1 = min(height_px, int(math.ceil((tz_max - z_min) / dz)) + 2)
        if ix0 >= ix1 or iz0 >= iz1:
            continue
        xx, zz = np.meshgrid(xs[ix0:ix1], zs[iz0:iz1])
        occupancy[iz0:iz1, ix0:ix1] |= _triangle_mask(xx, zz, triangle)

    if not np.any(occupancy):
        raise RuntimeError("Text contour rasterization produced an empty mask.")

    outside = distance_transform_edt(~occupancy, sampling=(dz, dx))
    inside = distance_transform_edt(occupancy, sampling=(dz, dx))
    sdf = outside - inside
    return sdf.astype(np.float32), x_min, x_max, z_min, z_max, natural_width, natural_height


def _sample_glyph_sdf(text: str, x, z):
    sdf, x_min, x_max, z_min, z_max, _, _ = _glyph_sdf(text or "TEXT")
    height_px, width_px = sdf.shape

    x_array = np.asarray(x, dtype=np.float64)
    z_array = np.asarray(z, dtype=np.float64)
    fx = (x_array - x_min) * (width_px - 1) / (x_max - x_min)
    fz = (z_array - z_min) * (height_px - 1) / (z_max - z_min)

    clipped_x = np.clip(fx, 0.0, width_px - 1.0)
    clipped_z = np.clip(fz, 0.0, height_px - 1.0)
    x0 = np.floor(clipped_x).astype(np.int64)
    z0 = np.floor(clipped_z).astype(np.int64)
    x1 = np.minimum(x0 + 1, width_px - 1)
    z1 = np.minimum(z0 + 1, height_px - 1)
    wx = clipped_x - x0
    wz = clipped_z - z0

    sampled = (
        (1.0 - wx) * (1.0 - wz) * sdf[z0, x0]
        + wx * (1.0 - wz) * sdf[z0, x1]
        + (1.0 - wx) * wz * sdf[z1, x0]
        + wx * wz * sdf[z1, x1]
    )

    # Outside the cached rectangle, extend the SDF with the Euclidean distance
    # to the rectangle instead of clamping to a false near-surface value.
    outside_x = np.maximum(np.maximum(x_min - x_array, x_array - x_max), 0.0)
    outside_z = np.maximum(np.maximum(z_min - z_array, z_array - z_max), 0.0)
    outside_distance = np.sqrt(outside_x * outside_x + outside_z * outside_z)
    return sampled + outside_distance


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
    _, _, _, _, _, natural_width, natural_height = _glyph_sdf(text or "TEXT")
    scale = min(total_width / natural_width, total_height / natural_height)
    if scale <= 0.0:
        return _ORIGINAL_FIELD(feature, u, depth_coordinate, v)

    planar = _sample_glyph_sdf(text or "TEXT", np.asarray(u) / scale, np.asarray(v) / scale) * scale
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
