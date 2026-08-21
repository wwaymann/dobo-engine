from __future__ import annotations

import numpy as np

from .cat_specification import OrganicCatSpecification
from .fields import (
    capped_cylinder_distance,
    capsule_distance,
    ellipsoid_distance,
    elliptical_column_distance,
    rounded_triangle_prism_distance,
    smooth_intersection,
    smooth_union,
)
from .specification import EllipsoidFieldSpec
from .vessel_engine import OrganicVesselEngine


def _ellipsoid(x, y, z, *, identifier: str, center, radii):
    return ellipsoid_distance(
        x,
        y,
        z,
        EllipsoidFieldSpec(id=identifier, center=center, radii=radii),
    )


class OrganicCatVesselEngine(OrganicVesselEngine):
    @classmethod
    def _ear_field(cls, specification, x, y, z, direction: float):
        ears = specification.cat.ears
        base_x = direction * ears.x_offset_mm
        half_width = 0.5 * ears.base_width_mm
        tip_x = base_x + direction * ears.tip_outward_mm
        triangle = rounded_triangle_prism_distance(
            x,
            y,
            z,
            vertices_xz=(
                (base_x - half_width, ears.base_z_mm),
                (base_x + half_width, ears.base_z_mm),
                (tip_x, ears.base_z_mm + ears.height_mm),
            ),
            center_y=ears.center_y_mm,
            half_depth=ears.half_depth_mm,
            round_mm=ears.round_mm,
        )
        lens = _ellipsoid(
            x,
            y,
            z,
            identifier="ear_lens",
            center=(
                base_x + direction * 0.35 * ears.tip_outward_mm,
                ears.center_y_mm,
                ears.base_z_mm + 0.42 * ears.height_mm,
            ),
            radii=(
                0.72 * ears.base_width_mm,
                1.15 * ears.half_depth_mm,
                0.72 * ears.height_mm,
            ),
        )
        return smooth_intersection(triangle, lens, ears.round_mm)

    @classmethod
    def _outer_field(cls, specification, x, y, z):
        outer = OrganicVesselEngine._outer_field(specification, x, y, z)
        ears = specification.cat.ears
        for direction in (-1.0, 1.0):
            outer = smooth_union(
                outer,
                cls._ear_field(specification, x, y, z, direction),
                ears.blend_mm,
            )

        face = specification.cat.face
        for direction in (-1.0, 1.0):
            muzzle = _ellipsoid(
                x,
                y,
                z,
                identifier="muzzle",
                center=(
                    direction * face.muzzle_x_offset_mm,
                    face.muzzle_center_y_mm,
                    face.muzzle_z_mm,
                ),
                radii=face.muzzle_radii_mm,
            )
            outer = smooth_union(outer, muzzle, face.muzzle_blend_mm)

        nose = _ellipsoid(
            x,
            y,
            z,
            identifier="nose",
            center=face.nose_center,
            radii=face.nose_radii_mm,
        )
        return smooth_union(outer, nose, face.nose_blend_mm)

    @classmethod
    def _face_removal(cls, specification, x, y, z):
        face = specification.cat.face
        eyes = []
        for direction in (-1.0, 1.0):
            center_x = direction * face.eye_x_offset_mm
            eyes.append(
                capsule_distance(
                    x,
                    y,
                    z,
                    start=(
                        center_x - direction * 0.5 * face.eye_length_mm,
                        face.eye_center_y_mm,
                        face.eye_z_mm - 0.5 * face.eye_tilt_mm,
                    ),
                    end=(
                        center_x + direction * 0.5 * face.eye_length_mm,
                        face.eye_center_y_mm,
                        face.eye_z_mm + 0.5 * face.eye_tilt_mm,
                    ),
                    radius=face.eye_radius_mm,
                )
            )
        removal = smooth_union(eyes[0], eyes[1], face.eye_blend_mm)

        center = (0.0, face.mouth_center_y_mm, face.mouth_z_mm)
        left = capsule_distance(
            x,
            y,
            z,
            start=center,
            end=(
                -face.mouth_half_width_mm,
                face.mouth_center_y_mm,
                face.mouth_z_mm - face.mouth_drop_mm,
            ),
            radius=face.mouth_radius_mm,
        )
        right = capsule_distance(
            x,
            y,
            z,
            start=center,
            end=(
                face.mouth_half_width_mm,
                face.mouth_center_y_mm,
                face.mouth_z_mm - face.mouth_drop_mm,
            ),
            radius=face.mouth_radius_mm,
        )
        mouth = smooth_union(left, right, face.mouth_blend_mm)
        philtrum = capsule_distance(
            x,
            y,
            z,
            start=(0.0, face.mouth_center_y_mm, face.mouth_z_mm + 1.8),
            end=center,
            radius=0.85 * face.mouth_radius_mm,
        )
        mouth = smooth_union(mouth, philtrum, face.mouth_blend_mm)
        return smooth_union(removal, mouth, face.mouth_blend_mm)

    @classmethod
    def _feature_refinement_weights(cls, specification, vertices):
        x = vertices[:, 0]
        y = vertices[:, 1]
        z = vertices[:, 2]
        face = np.clip((-y - 33.0) / 5.0, 0.0, 1.0)
        face *= np.clip((21.0 - np.abs(x)) / 5.0, 0.0, 1.0)
        face *= np.clip((18.0 - np.abs(z - 5.0)) / 5.0, 0.0, 1.0)
        return face

    @classmethod
    def _material_field(cls, specification, x, y, z):
        vessel = specification.vessel
        base_outer = OrganicVesselEngine._outer_field(specification, x, y, z)
        cat_outer = cls._outer_field(specification, x, y, z)

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
        removal = smooth_union(offset_cavity, opening, vessel.opening_blend_mm)
        shell = smooth_intersection(cat_outer, -removal, vessel.rim_round_mm)
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
        return np.maximum(
            material,
            -cls._face_removal(specification, x, y, z),
        )

    @classmethod
    def character_checks(cls, specification: OrganicCatSpecification) -> dict[str, bool]:
        ears = specification.cat.ears
        face = specification.cat.face

        def sample(point) -> float:
            return float(
                cls._material_field(
                    specification,
                    np.asarray(point[0]),
                    np.asarray(point[1]),
                    np.asarray(point[2]),
                )
            )

        return {
            "left_ear_tip_is_solid": sample(
                (
                    -ears.x_offset_mm - ears.tip_outward_mm,
                    ears.center_y_mm,
                    ears.base_z_mm + ears.height_mm - 1.5 * ears.round_mm,
                )
            ) < 0.0,
            "right_ear_tip_is_solid": sample(
                (
                    ears.x_offset_mm + ears.tip_outward_mm,
                    ears.center_y_mm,
                    ears.base_z_mm + ears.height_mm - 1.5 * ears.round_mm,
                )
            ) < 0.0,
            "left_eye_is_recessed": sample(
                (-face.eye_x_offset_mm, face.eye_center_y_mm, face.eye_z_mm)
            ) > 0.0,
            "right_eye_is_recessed": sample(
                (face.eye_x_offset_mm, face.eye_center_y_mm, face.eye_z_mm)
            ) > 0.0,
            "left_muzzle_is_solid": sample(
                (
                    -face.muzzle_x_offset_mm,
                    face.muzzle_center_y_mm,
                    face.muzzle_z_mm,
                )
            ) < 0.0,
            "right_muzzle_is_solid": sample(
                (
                    face.muzzle_x_offset_mm,
                    face.muzzle_center_y_mm,
                    face.muzzle_z_mm,
                )
            ) < 0.0,
            "nose_is_solid": sample(face.nose_center) < 0.0,
            "mouth_center_is_recessed": sample(
                (0.0, face.mouth_center_y_mm, face.mouth_z_mm)
            ) > 0.0,
        }
