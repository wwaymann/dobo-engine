from __future__ import annotations

import numpy as np

from .feature_program_specification import FeatureInstruction, FeatureProgramSpecification
from .fields import (
    arched_prism_distance,
    capped_cylinder_distance,
    capsule_distance,
    ellipsoid_distance,
    elliptical_column_distance,
    implicit_field_distance,
    rounded_box_distance,
    rounded_triangle_prism_distance,
    smooth_intersection,
    smooth_union,
)
from .specification import AdvancedFieldSpec, EllipsoidFieldSpec
from .vessel_engine import OrganicVesselEngine


class FeatureProgramVesselEngine(OrganicVesselEngine):
    """Evaluate reusable organic and structural feature instructions."""

    @staticmethod
    def _feature_field(feature: FeatureInstruction, x, y, z):
        if feature.kind == "ellipsoid":
            return ellipsoid_distance(
                x,
                y,
                z,
                EllipsoidFieldSpec(
                    id=feature.id,
                    center=feature.center,
                    radii=feature.radii,
                ),
            )
        if feature.kind == "capsule":
            return capsule_distance(
                x, y, z, start=feature.start, end=feature.end, radius=feature.radius_mm
            )
        if feature.kind == "rounded_box":
            return rounded_box_distance(
                x,
                y,
                z,
                center=feature.center,
                half_sizes=feature.half_sizes,
                round_mm=feature.round_mm,
            )
        if feature.kind == "cylinder":
            return capped_cylinder_distance(
                x,
                y,
                z,
                center=feature.center,
                radius=feature.radius_mm,
                half_height=feature.half_height_mm,
            )
        if feature.kind == "rounded_triangle_prism":
            return rounded_triangle_prism_distance(
                x,
                y,
                z,
                vertices_xz=feature.vertices_xz,
                center_y=feature.center_y_mm,
                half_depth=feature.half_depth_mm,
                round_mm=feature.round_mm,
            )
        if feature.kind in {
            "superellipsoid",
            "faceted_ellipsoid",
            "leaf",
            "pointed",
        }:
            return implicit_field_distance(
                x,
                y,
                z,
                AdvancedFieldSpec(
                    id=feature.id,
                    kind=feature.kind,
                    center=feature.center,
                    radii=feature.radii,
                    exponent=feature.exponent,
                    sides=feature.sides,
                    rotation_degrees=feature.rotation_degrees,
                    round_mm=feature.round_mm,
                ),
            )
        return arched_prism_distance(
            x,
            y,
            z,
            center_x=feature.center[0],
            center_y=feature.center[1],
            bottom_z=feature.bottom_z_mm,
            spring_z=feature.spring_z_mm,
            half_width=feature.half_width_mm,
            half_depth=feature.half_depth_mm,
            round_mm=feature.round_mm,
        )

    @classmethod
    def _outer_field(cls, specification, x, y, z):
        outer = OrganicVesselEngine._outer_field(specification, x, y, z)
        for feature in specification.features:
            if feature.operation == "add":
                outer = smooth_union(
                    outer,
                    cls._feature_field(feature, x, y, z),
                    feature.blend_mm,
                )
        return outer

    @classmethod
    def _subtraction_field(cls, specification, x, y, z):
        subtractors = tuple(
            feature for feature in specification.features if feature.operation == "subtract"
        )
        removal = cls._feature_field(subtractors[0], x, y, z)
        for feature in subtractors[1:]:
            removal = smooth_union(
                removal,
                cls._feature_field(feature, x, y, z),
                feature.blend_mm,
            )
        return removal

    @classmethod
    def _material_field(cls, specification, x, y, z):
        vessel = specification.vessel
        base_outer = OrganicVesselEngine._outer_field(specification, x, y, z)
        featured_outer = cls._outer_field(specification, x, y, z)
        offset_cavity = np.maximum(
            base_outer + vessel.wall_mm,
            vessel.cavity_floor_z_mm - z,
        )
        opening = np.maximum(
            elliptical_column_distance(
                x,
                y,
                center=vessel.opening_center,
                radii=vessel.opening_radii,
            ),
            vessel.opening_start_z_mm - z,
        )
        cavity = smooth_union(offset_cavity, opening, vessel.opening_blend_mm)
        shell = smooth_intersection(featured_outer, -cavity, vessel.rim_round_mm)
        material = np.maximum(shell, vessel.base_z_mm - z)

        drain_center_z = 0.5 * (vessel.drain_start_z_mm + vessel.drain_end_z_mm)
        drain = capped_cylinder_distance(
            x,
            y,
            z,
            center=(vessel.drain_center[0], vessel.drain_center[1], drain_center_z),
            radius=vessel.drain_radius_mm,
            half_height=0.5 * (vessel.drain_end_z_mm - vessel.drain_start_z_mm),
        )
        material = np.maximum(material, -drain)
        if any(feature.operation == "subtract" for feature in specification.features):
            material = np.maximum(
                material,
                -cls._subtraction_field(specification, x, y, z),
            )
        return material

    @classmethod
    def _feature_refinement_weights(cls, specification, vertices):
        # Grid extraction preserves deliberate hard/soft transitions; localized
        # refinement remains dedicated to the continuous vessel rim.
        return np.zeros(len(vertices), dtype=np.float64)

    @classmethod
    def feature_checks(
        cls, specification: FeatureProgramSpecification
    ) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        for feature in specification.features:
            value = float(
                cls._material_field(
                    specification,
                    np.asarray(feature.probe[0]),
                    np.asarray(feature.probe[1]),
                    np.asarray(feature.probe[2]),
                )
            )
            expected_inside = feature.operation == "add"
            checks[f"{feature.operation}_{feature.id}"] = (
                value < 0.0 if expected_inside else value > 0.0
            )
        return checks
