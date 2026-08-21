from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .specification import AdvancedFieldSpec, EllipsoidFieldSpec, ImplicitFieldSpec


FloatArray = NDArray[np.floating]


def ellipsoid_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    specification: EllipsoidFieldSpec,
) -> FloatArray:
    """Return Inigo Quilez's stable ellipsoid SDF approximation."""
    center = specification.center
    radii = specification.radii
    px = x - center[0]
    py = y - center[1]
    pz = z - center[2]
    k0 = np.sqrt(
        (px / radii[0]) ** 2
        + (py / radii[1]) ** 2
        + (pz / radii[2]) ** 2
    )
    k1 = np.sqrt(
        (px / (radii[0] ** 2)) ** 2
        + (py / (radii[1] ** 2)) ** 2
        + (pz / (radii[2] ** 2)) ** 2
    )
    numerator = k0 * (k0 - 1.0)
    fallback = np.full_like(k0, -min(radii))
    return np.divide(
        numerator,
        k1,
        out=fallback,
        where=k1 > 1e-12,
    )


def superellipsoid_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    specification: AdvancedFieldSpec,
) -> FloatArray:
    """Continuous rounded-volume field controlled by a reusable exponent."""
    px = np.abs((x - specification.center[0]) / specification.radii[0])
    py = np.abs((y - specification.center[1]) / specification.radii[1])
    pz = np.abs((z - specification.center[2]) / specification.radii[2])
    exponent = specification.exponent
    normalized = (px**exponent + py**exponent + pz**exponent) ** (
        1.0 / exponent
    )
    return (normalized - 1.0) * min(specification.radii)


def faceted_ellipsoid_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    specification: AdvancedFieldSpec,
) -> FloatArray:
    """Rounded regular-polygon body with ellipsoidal vertical closure."""
    px = (x - specification.center[0]) / specification.radii[0]
    py = (y - specification.center[1]) / specification.radii[1]
    pz = np.abs((z - specification.center[2]) / specification.radii[2])
    angle = np.arctan2(py, px) - np.deg2rad(specification.rotation_degrees)
    sector = 2.0 * np.pi / specification.sides
    local = np.mod(angle + 0.5 * sector, sector) - 0.5 * sector
    polygon_radius = np.cos(0.5 * sector) / np.cos(local)
    radial = np.sqrt(px * px + py * py) / polygon_radius
    exponent = specification.exponent
    normalized = (radial**exponent + pz**exponent) ** (1.0 / exponent)
    return (normalized - 1.0) * min(specification.radii)


def leaf_volume_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    specification: AdvancedFieldSpec,
) -> FloatArray:
    """Pointed lens in X/Z with a softly rounded finite depth."""
    px = x - specification.center[0]
    py = y - specification.center[1]
    pz = z - specification.center[2]
    half_width, half_depth, half_height = specification.radii
    lens_radius = (half_height**2 + half_width**2) / (2.0 * half_width)
    lens_offset = lens_radius - half_width
    first = np.sqrt((px - lens_offset) ** 2 + pz**2) - lens_radius
    second = np.sqrt((px + lens_offset) ** 2 + pz**2) - lens_radius
    lens = np.maximum(first, second)
    depth = np.abs(py) - half_depth
    rounding = min(specification.round_mm, 0.45 * half_depth)
    return smooth_intersection(lens, depth, rounding)


def pointed_volume_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    specification: AdvancedFieldSpec,
) -> FloatArray:
    """Rounded triangular point suitable for ears, horns and crown lobes."""
    cx, cy, cz = specification.center
    rx, ry, rz = specification.radii
    return rounded_triangle_prism_distance(
        x,
        y,
        z,
        vertices_xz=((cx - rx, cz - rz), (cx + rx, cz - rz), (cx, cz + rz)),
        center_y=cy,
        half_depth=ry,
        round_mm=min(specification.round_mm, 0.45 * min(rx, ry, rz)),
    )


def implicit_field_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    specification: ImplicitFieldSpec,
) -> FloatArray:
    """Dispatch legacy and Block-6 implicit fields through one stable contract."""
    if isinstance(specification, EllipsoidFieldSpec):
        return ellipsoid_distance(x, y, z, specification)
    if specification.kind == "superellipsoid":
        return superellipsoid_distance(x, y, z, specification)
    if specification.kind == "faceted_ellipsoid":
        return faceted_ellipsoid_distance(x, y, z, specification)
    if specification.kind == "leaf":
        return leaf_volume_distance(x, y, z, specification)
    return pointed_volume_distance(x, y, z, specification)


def smooth_union(a: FloatArray, b: FloatArray, blend_mm: float) -> FloatArray:
    """Polynomial smooth minimum: negative values are inside the solid."""
    if blend_mm <= 0.0:
        raise ValueError("blend_mm must be positive.")
    h = np.clip(0.5 + 0.5 * (b - a) / blend_mm, 0.0, 1.0)
    return b * (1.0 - h) + a * h - blend_mm * h * (1.0 - h)


def smooth_intersection(a: FloatArray, b: FloatArray, blend_mm: float) -> FloatArray:
    """Smooth maximum for intersecting negative-inside fields."""
    return -smooth_union(-a, -b, blend_mm)


def elliptical_column_distance(
    x: FloatArray,
    y: FloatArray,
    *,
    center: tuple[float, float],
    radii: tuple[float, float],
) -> FloatArray:
    """Approximate signed distance to an infinite elliptical column."""
    if radii[0] <= 0.0 or radii[1] <= 0.0:
        raise ValueError("Elliptical column radii must be positive.")
    normalized = np.sqrt(
        ((x - center[0]) / radii[0]) ** 2
        + ((y - center[1]) / radii[1]) ** 2
    )
    return (normalized - 1.0) * min(radii)


def capped_cylinder_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    center: tuple[float, float, float],
    radius: float,
    half_height: float,
) -> FloatArray:
    """Signed distance to a vertical capped cylinder."""
    if radius <= 0.0 or half_height <= 0.0:
        raise ValueError("Capped cylinder dimensions must be positive.")
    radial = np.sqrt(
        (x - center[0]) ** 2
        + (y - center[1]) ** 2
    ) - radius
    axial = np.abs(z - center[2]) - half_height
    outside = np.sqrt(np.maximum(radial, 0.0) ** 2 + np.maximum(axial, 0.0) ** 2)
    inside = np.minimum(np.maximum(radial, axial), 0.0)
    return outside + inside


def capsule_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
) -> FloatArray:
    """Signed distance to a capsule joining two three-dimensional points."""
    if radius <= 0.0:
        raise ValueError("Capsule radius must be positive.")
    segment = np.asarray(end, dtype=np.float64) - np.asarray(start, dtype=np.float64)
    length_squared = float(np.dot(segment, segment))
    if length_squared <= 1e-12:
        raise ValueError("Capsule endpoints must be distinct.")
    px = x - start[0]
    py = y - start[1]
    pz = z - start[2]
    projection = np.clip(
        (px * segment[0] + py * segment[1] + pz * segment[2])
        / length_squared,
        0.0,
        1.0,
    )
    dx = px - projection * segment[0]
    dy = py - projection * segment[1]
    dz = pz - projection * segment[2]
    return np.sqrt(dx * dx + dy * dy + dz * dz) - radius


def rounded_triangle_prism_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    vertices_xz: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ],
    center_y: float,
    half_depth: float,
    round_mm: float,
) -> FloatArray:
    """Approximate SDF for a softly rounded triangular prism."""
    if half_depth <= 0.0 or round_mm <= 0.0:
        raise ValueError("Rounded triangle prism dimensions must be positive.")
    points = np.asarray(vertices_xz, dtype=np.float64)
    signed_edges = []
    for index in range(3):
        start = points[index]
        end = points[(index + 1) % 3]
        edge = end - start
        length = float(np.linalg.norm(edge))
        if length <= 1e-12:
            raise ValueError("Triangle prism vertices must be distinct.")
        cross = edge[0] * (z - start[1]) - edge[1] * (x - start[0])
        signed_edges.append(-cross / length)
    triangle = smooth_intersection(signed_edges[0], signed_edges[1], round_mm)
    triangle = smooth_intersection(triangle, signed_edges[2], round_mm)
    depth = np.abs(y - center_y) - half_depth
    return smooth_intersection(triangle, depth, 0.6 * round_mm)


def rounded_box_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    center: tuple[float, float, float],
    half_sizes: tuple[float, float, float],
    round_mm: float,
) -> FloatArray:
    """Signed distance to an axis-aligned rounded box."""
    if any(size <= 0.0 for size in half_sizes):
        raise ValueError("Rounded-box half sizes must be positive.")
    if round_mm <= 0.0 or round_mm >= min(half_sizes):
        raise ValueError("Rounded-box radius must fit inside every half size.")
    qx = np.abs(x - center[0]) - (half_sizes[0] - round_mm)
    qy = np.abs(y - center[1]) - (half_sizes[1] - round_mm)
    qz = np.abs(z - center[2]) - (half_sizes[2] - round_mm)
    outside = np.sqrt(
        np.maximum(qx, 0.0) ** 2
        + np.maximum(qy, 0.0) ** 2
        + np.maximum(qz, 0.0) ** 2
    )
    inside = np.minimum(np.maximum(np.maximum(qx, qy), qz), 0.0)
    return outside + inside - round_mm


def arched_prism_distance(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    center_x: float,
    center_y: float,
    bottom_z: float,
    spring_z: float,
    half_width: float,
    half_depth: float,
    round_mm: float,
) -> FloatArray:
    """Approximate SDF for a vertical round-arched prism."""
    if spring_z <= bottom_z:
        raise ValueError("Arched-prism spring_z must be above bottom_z.")
    if min(half_width, half_depth, round_mm) <= 0.0:
        raise ValueError("Arched-prism dimensions must be positive.")
    lower_center_z = 0.5 * (bottom_z + spring_z)
    lower_round = min(
        round_mm,
        0.45 * (spring_z - bottom_z),
        0.45 * half_width,
        0.45 * half_depth,
    )
    lower = rounded_box_distance(
        x,
        y,
        z,
        center=(center_x, center_y, lower_center_z),
        half_sizes=(half_width, half_depth, 0.5 * (spring_z - bottom_z)),
        round_mm=lower_round,
    )
    radial = np.sqrt((x - center_x) ** 2 + (z - spring_z) ** 2) - half_width
    depth = np.abs(y - center_y) - half_depth
    outside = np.sqrt(
        np.maximum(radial, 0.0) ** 2 + np.maximum(depth, 0.0) ** 2
    )
    inside = np.minimum(np.maximum(radial, depth), 0.0)
    crown = outside + inside
    crown = np.maximum(crown, spring_z - z)
    return smooth_union(lower, crown, round_mm)
