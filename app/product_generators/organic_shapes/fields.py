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
