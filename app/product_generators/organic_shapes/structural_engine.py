from __future__ import annotations

import numpy as np

from .fields import (
    arched_prism_distance,
    capped_cylinder_distance,
    capsule_distance,
    elliptical_column_distance,
    rounded_box_distance,
    smooth_intersection,
    smooth_union,
)
from .structural_specification import (
    StructuralCutoutSpec,
    StructuralPrimitiveSpec,
    StructuralVesselSpecification,
)
from .vessel_engine import OrganicVesselEngine


class StructuralVesselEngine(OrganicVesselEngine):
    @staticmethod
    def _primitive_field(primitive: StructuralPrimitiveSpec, x, y, z):
        if primitive.kind == "rounded_box":
            return rounded_box_distance(
                x,
                y,
                z,
                center=primitive.center,
                half_sizes=primitive.half_sizes,
                round_mm=primitive.round_mm,
            )
        return capped_cylinder_distance(
            x,
            y,
            z,
            center=primitive.center,
            radius=primitive.radius_mm,
            half_height=primitive.half_height_mm,
        )

    @staticmethod
    def _cutout_field(cutout: StructuralCutoutSpec, x, y, z):
        if cutout.kind == "rounded_box":
            return rounded_box_distance(
                x,
                y,
                z,
                center=cutout.center,
                half_sizes=cutout.half_sizes,
                round_mm=cutout.round_mm,
            )
        if cutout.kind == "capsule":
            return capsule_distance(
                x,
                y,
                z,
                start=cutout.start,
                end=cutout.end,
                radius=cutout.radius_mm,
            )
        return arched_prism_distance(
            x,
            y,
            z,
            center_x=cutout.center[0],
            center_y=cutout.center[1],
            bottom_z=cutout.bottom_z_mm,
            spring_z=cutout.spring_z_mm,
            half_width=cutout.half_width_mm,
            half_depth=cutout.half_depth_mm,
            round_mm=cutout.round_mm,
        )

    @classmethod
    def _outer_field(cls, specification, x, y, z):
        outer = OrganicVesselEngine._outer_field(specification, x, y, z)
        for addition in specification.structure.additions:
            outer = smooth_union(
                outer,
                cls._primitive_field(addition, x, y, z),
                addition.blend_mm,
            )
        return outer

    @classmethod
    def _cutouts_field(cls, specification, x, y, z):
        cutouts = specification.structure.cutouts
        removal = cls._cutout_field(cutouts[0], x, y, z)
        for cutout in cutouts[1:]:
            removal = smooth_union(
                removal,
                cls._cutout_field(cutout, x, y, z),
                cutout.blend_mm,
            )
        return removal

    @classmethod
    def _material_field(cls, specification, x, y, z):
        vessel = specification.vessel
        base_outer = OrganicVesselEngine._outer_field(specification, x, y, z)
        structural_outer = cls._outer_field(specification, x, y, z)
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
        shell = smooth_intersection(structural_outer, -cavity, vessel.rim_round_mm)
        material = np.maximum(shell, vessel.base_z_mm - z)

        drain_center_z = 0.5 * (
            vessel.drain_start_z_mm + vessel.drain_end_z_mm
        )
        drain = capped_cylinder_distance(
            x,
            y,
            z,
            center=(vessel.drain_center[0], vessel.drain_center[1], drain_center_z),
            radius=vessel.drain_radius_mm,
            half_height=0.5 * (
                vessel.drain_end_z_mm - vessel.drain_start_z_mm
            ),
        )
        material = np.maximum(material, -drain)
        if specification.structure.cutouts:
            material = np.maximum(
                material,
                -cls._cutouts_field(specification, x, y, z),
            )
        return material

    @classmethod
    def _feature_refinement_weights(cls, specification, vertices):
        # Structural cutouts are already sampled at the requested grid resolution.
        # Refining their hard edges selectively can create T-junctions and softens
        # the architectural profile, so only the vessel's continuous rim is refined.
        return np.zeros(len(vertices), dtype=np.float64)

    @classmethod
    def structural_checks(
        cls,
        specification: StructuralVesselSpecification,
    ) -> dict[str, bool]:
        def sample(point) -> float:
            return float(
                cls._material_field(
                    specification,
                    np.asarray(point[0]),
                    np.asarray(point[1]),
                    np.asarray(point[2]),
                )
            )

        checks: dict[str, bool] = {}
        for addition in specification.structure.additions:
            forward_extent = (
                addition.half_sizes[1]
                if addition.kind == "rounded_box"
                else addition.radius_mm
            )
            vertical_extent = (
                addition.half_sizes[2]
                if addition.kind == "rounded_box"
                else addition.half_height_mm
            )
            probes = (
                (
                    addition.center[0],
                    addition.center[1] - forward_fraction * forward_extent,
                    addition.center[2] + vertical_fraction * vertical_extent,
                )
                for forward_fraction in (0.65, 0.8, 0.9)
                for vertical_fraction in (-0.2, 0.0, 0.2)
            )
            checks[f"addition_{addition.id}_is_solid"] = any(
                sample(probe) < 0.0 for probe in probes
            )
        for cutout in specification.structure.cutouts:
            checks[f"cutout_{cutout.id}_is_clear"] = sample(cutout.center) > 0.0
        return checks
