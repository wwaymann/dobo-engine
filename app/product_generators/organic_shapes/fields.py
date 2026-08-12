from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .specification import EllipsoidFieldSpec


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
