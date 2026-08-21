from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite, radians, sin
from typing import Callable

import numpy as np


ScalarField = Callable[[float, float, float], float]


@dataclass(frozen=True, slots=True)
class SurfaceAnchorSpec:
    """Body-relative location resolved against the unfeatured outer surface."""

    azimuth_degrees: float
    height_ratio: float
    offset_mm: float = 0.0
    roll_degrees: float = 0.0

    def validate(self) -> None:
        values = (
            self.azimuth_degrees,
            self.height_ratio,
            self.offset_mm,
            self.roll_degrees,
        )
        if not all(isfinite(value) for value in values):
            raise ValueError("Surface-anchor values must be finite.")
        if not 0.0 <= self.height_ratio <= 1.0:
            raise ValueError("Surface-anchor height_ratio must be between 0 and 1.")
        if abs(self.offset_mm) > 20.0:
            raise ValueError("Surface-anchor offset_mm cannot exceed 20 mm.")


@dataclass(frozen=True, slots=True)
class ResolvedSurfaceAnchor:
    surface_point: tuple[float, float, float]
    origin: tuple[float, float, float]
    outward_normal: tuple[float, float, float]
    matrix: np.ndarray
    surface_residual_mm: float
    radial_distance_mm: float


class SurfaceAnchorResolver:
    @classmethod
    def resolve(
        cls,
        anchor: SurfaceAnchorSpec,
        *,
        field_sampler: ScalarField,
        base_z_mm: float,
        opening_start_z_mm: float,
        maximum_radius_mm: float,
        gradient_epsilon_mm: float,
    ) -> ResolvedSurfaceAnchor:
        anchor.validate()
        if opening_start_z_mm <= base_z_mm:
            raise ValueError("Surface anchoring requires opening above the base.")
        if maximum_radius_mm <= 0.0 or gradient_epsilon_mm <= 0.0:
            raise ValueError("Surface-anchor search dimensions must be positive.")

        angle = radians(anchor.azimuth_degrees)
        direction = np.asarray((sin(angle), -cos(angle)), dtype=np.float64)
        z = base_z_mm + anchor.height_ratio * (
            opening_start_z_mm - base_z_mm
        )

        def radial_sample(radius: float) -> float:
            return float(
                field_sampler(
                    radius * direction[0],
                    radius * direction[1],
                    z,
                )
            )

        low = 0.0
        high = maximum_radius_mm
        if radial_sample(low) >= 0.0:
            raise RuntimeError("Surface-anchor ray does not start inside the body.")
        while radial_sample(high) <= 0.0 and high < 4.0 * maximum_radius_mm:
            high *= 1.5
        if radial_sample(high) <= 0.0:
            raise RuntimeError("Surface-anchor ray did not leave the body.")
        for _ in range(48):
            middle = 0.5 * (low + high)
            if radial_sample(middle) <= 0.0:
                low = middle
            else:
                high = middle
        radius = 0.5 * (low + high)
        surface = np.asarray(
            (radius * direction[0], radius * direction[1], z),
            dtype=np.float64,
        )
        epsilon = gradient_epsilon_mm
        gradient = np.empty(3, dtype=np.float64)
        for axis in range(3):
            plus = surface.copy()
            minus = surface.copy()
            plus[axis] += epsilon
            minus[axis] -= epsilon
            gradient[axis] = (
                field_sampler(*plus) - field_sampler(*minus)
            ) / (2.0 * epsilon)
        length = float(np.linalg.norm(gradient))
        if length <= 1e-9:
            raise RuntimeError("Surface-anchor normal is undefined.")
        normal = gradient / length

        local_y = -normal
        up = np.asarray((0.0, 0.0, 1.0), dtype=np.float64)
        local_z = up - float(np.dot(up, normal)) * normal
        if np.linalg.norm(local_z) <= 1e-6:
            fallback = np.asarray((1.0, 0.0, 0.0), dtype=np.float64)
            local_z = fallback - float(np.dot(fallback, normal)) * normal
        local_z /= np.linalg.norm(local_z)
        local_x = np.cross(local_y, local_z)
        local_x /= np.linalg.norm(local_x)

        roll = radians(anchor.roll_degrees)
        rolled_x = cos(roll) * local_x + sin(roll) * local_z
        rolled_z = -sin(roll) * local_x + cos(roll) * local_z
        origin = surface + anchor.offset_mm * normal
        matrix = np.eye(4, dtype=np.float64)
        matrix[:3, 0] = rolled_x
        matrix[:3, 1] = local_y
        matrix[:3, 2] = rolled_z
        matrix[:3, 3] = origin
        residual = abs(float(field_sampler(*surface)))
        return ResolvedSurfaceAnchor(
            surface_point=tuple(float(value) for value in surface),
            origin=tuple(float(value) for value in origin),
            outward_normal=tuple(float(value) for value in normal),
            matrix=matrix,
            surface_residual_mm=residual,
            radial_distance_mm=radius,
        )
