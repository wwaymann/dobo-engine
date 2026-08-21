from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .feature_program_specification import FeatureInstruction


@dataclass(frozen=True, slots=True)
class AdaptiveFeatureRefinementContract:
    """Controls automatic local density around composed feature surfaces."""

    surface_band_mm: float
    size_band_ratio: float
    maximum_band_mm: float
    small_feature_threshold_mm: float
    detail_subdivision_passes: int

    def validate(self) -> None:
        positive = {
            "surface_band_mm": self.surface_band_mm,
            "size_band_ratio": self.size_band_ratio,
            "maximum_band_mm": self.maximum_band_mm,
            "small_feature_threshold_mm": self.small_feature_threshold_mm,
        }
        invalid = [name for name, value in positive.items() if value <= 0.0]
        if invalid:
            raise ValueError(
                f"Adaptive-refinement values must be positive: {invalid}"
            )
        if self.maximum_band_mm < self.surface_band_mm:
            raise ValueError(
                "adaptive_refinement.maximum_band_mm must be at least surface_band_mm."
            )
        if not 1 <= self.detail_subdivision_passes <= 2:
            raise ValueError(
                "adaptive_refinement.detail_subdivision_passes must be between 1 and 2."
            )

    def influence_band_mm(self, feature_size_mm: float) -> float:
        return min(
            self.maximum_band_mm,
            max(self.surface_band_mm, self.size_band_ratio * feature_size_mm),
        )


def feature_characteristic_size(feature: FeatureInstruction) -> float:
    """Return the smallest deliberate scale that controls visible curvature."""

    if feature.kind == "ellipsoid":
        assert feature.radii is not None
        return min(feature.radii)
    if feature.kind == "capsule":
        assert feature.radius_mm is not None
        return feature.radius_mm
    if feature.kind == "rounded_box":
        assert feature.half_sizes is not None and feature.round_mm is not None
        return min(feature.round_mm, *feature.half_sizes)
    if feature.kind == "cylinder":
        assert feature.radius_mm is not None and feature.half_height_mm is not None
        return min(feature.radius_mm, feature.half_height_mm)
    if feature.kind == "rounded_triangle_prism":
        assert feature.round_mm is not None and feature.half_depth_mm is not None
        return min(feature.round_mm, feature.half_depth_mm)
    assert feature.kind == "arched_prism"
    assert feature.round_mm is not None and feature.half_width_mm is not None
    assert feature.half_depth_mm is not None
    return min(feature.round_mm, feature.half_width_mm, feature.half_depth_mm)


def surface_proximity_weights(
    signed_distance: np.ndarray,
    *,
    band_mm: float,
    feature_size_mm: float,
    small_feature_threshold_mm: float,
) -> np.ndarray:
    proximity = np.clip(1.0 - np.abs(signed_distance) / band_mm, 0.0, 1.0)
    size_priority = np.clip(
        small_feature_threshold_mm / max(feature_size_mm, 1e-9),
        1.0,
        2.0,
    )
    return np.clip(proximity * size_priority, 0.0, 1.0)
