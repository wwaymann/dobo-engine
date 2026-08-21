from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .vessel_specification import (
    OrganicVesselParser,
    OrganicVesselSpecification,
    _vector2,
)
from .specification import _object, _vector3


@dataclass(frozen=True, slots=True)
class OrganicCatEarContract:
    x_offset_mm: float
    base_z_mm: float
    height_mm: float
    center_y_mm: float
    base_width_mm: float
    half_depth_mm: float
    round_mm: float
    tip_outward_mm: float
    blend_mm: float

    def validate(self) -> None:
        positive = {
            "x_offset_mm": self.x_offset_mm,
            "height_mm": self.height_mm,
            "base_width_mm": self.base_width_mm,
            "half_depth_mm": self.half_depth_mm,
            "round_mm": self.round_mm,
            "tip_outward_mm": self.tip_outward_mm,
            "blend_mm": self.blend_mm,
        }
        invalid = [name for name, value in positive.items() if value <= 0.0]
        if invalid:
            raise ValueError(f"Cat ear values must be positive: {invalid}")
        if self.round_mm * 2.0 >= min(self.base_width_mm, self.height_mm):
            raise ValueError("Cat ear rounding consumes its silhouette.")


@dataclass(frozen=True, slots=True)
class OrganicCatFaceContract:
    eye_x_offset_mm: float
    eye_center_y_mm: float
    eye_z_mm: float
    eye_length_mm: float
    eye_tilt_mm: float
    eye_radius_mm: float
    eye_blend_mm: float
    muzzle_x_offset_mm: float
    muzzle_center_y_mm: float
    muzzle_z_mm: float
    muzzle_radii_mm: tuple[float, float, float]
    muzzle_blend_mm: float
    nose_center: tuple[float, float, float]
    nose_radii_mm: tuple[float, float, float]
    nose_blend_mm: float
    mouth_center_y_mm: float
    mouth_z_mm: float
    mouth_half_width_mm: float
    mouth_drop_mm: float
    mouth_radius_mm: float
    mouth_blend_mm: float

    def validate(self) -> None:
        if self.eye_x_offset_mm <= 0.0 or self.muzzle_x_offset_mm <= 0.0:
            raise ValueError("Cat facial offsets must be positive.")
        for name, radii in (
            ("muzzle_radii_mm", self.muzzle_radii_mm),
            ("nose_radii_mm", self.nose_radii_mm),
        ):
            if any(value <= 0.0 for value in radii):
                raise ValueError(f"cat.face.{name} must be positive.")
        positive = {
            "eye_blend_mm": self.eye_blend_mm,
            "eye_length_mm": self.eye_length_mm,
            "eye_tilt_mm": self.eye_tilt_mm,
            "eye_radius_mm": self.eye_radius_mm,
            "muzzle_blend_mm": self.muzzle_blend_mm,
            "nose_blend_mm": self.nose_blend_mm,
            "mouth_half_width_mm": self.mouth_half_width_mm,
            "mouth_drop_mm": self.mouth_drop_mm,
            "mouth_radius_mm": self.mouth_radius_mm,
            "mouth_blend_mm": self.mouth_blend_mm,
        }
        invalid = [name for name, value in positive.items() if value <= 0.0]
        if invalid:
            raise ValueError(f"Cat face values must be positive: {invalid}")


@dataclass(frozen=True, slots=True)
class OrganicCatContract:
    ears: OrganicCatEarContract
    face: OrganicCatFaceContract

    def validate(self) -> None:
        self.ears.validate()
        self.face.validate()


@dataclass(frozen=True, slots=True)
class OrganicCatSpecification:
    vessel_specification: OrganicVesselSpecification
    cat: OrganicCatContract

    @property
    def id(self):
        return self.vessel_specification.id

    @property
    def grid(self):
        return self.vessel_specification.grid

    @property
    def fields(self):
        return self.vessel_specification.fields

    @property
    def composition(self):
        return self.vessel_specification.composition

    @property
    def vessel(self):
        return self.vessel_specification.vessel

    @property
    def mesh_quality(self):
        return self.vessel_specification.mesh_quality

    @property
    def output(self):
        return self.vessel_specification.output

    def validate(self) -> None:
        self.vessel_specification.validate()
        self.cat.validate()
        ear_tip = self.cat.ears.base_z_mm + self.cat.ears.height_mm
        if ear_tip >= self.grid.maximum[2] - 2.0 * self.grid.voxel_mm:
            raise ValueError("Cat ear tips require more upper grid clearance.")
        if self.cat.ears.base_z_mm <= self.vessel.opening_start_z_mm - 8.0:
            raise ValueError("Cat ear roots must begin near the planter crown.")


class OrganicCatParser:
    def parse_file(self, path: str | Path) -> OrganicCatSpecification:
        source = Path(path).resolve()
        import json

        return self.parse_dict(json.loads(source.read_text(encoding="utf-8")))

    def parse_dict(self, data: dict[str, Any]) -> OrganicCatSpecification:
        vessel_specification = OrganicVesselParser().parse_dict(data)
        cat = _object(data, "cat")
        ears = _object(cat, "ears")
        face = _object(cat, "face")
        specification = OrganicCatSpecification(
            vessel_specification=vessel_specification,
            cat=OrganicCatContract(
                ears=OrganicCatEarContract(
                    x_offset_mm=float(ears["x_offset_mm"]),
                    base_z_mm=float(ears["base_z_mm"]),
                    height_mm=float(ears["height_mm"]),
                    center_y_mm=float(ears["center_y_mm"]),
                    base_width_mm=float(ears["base_width_mm"]),
                    half_depth_mm=float(ears["half_depth_mm"]),
                    round_mm=float(ears["round_mm"]),
                    tip_outward_mm=float(ears["tip_outward_mm"]),
                    blend_mm=float(ears["blend_mm"]),
                ),
                face=OrganicCatFaceContract(
                    eye_x_offset_mm=float(face["eye_x_offset_mm"]),
                    eye_center_y_mm=float(face["eye_center_y_mm"]),
                    eye_z_mm=float(face["eye_z_mm"]),
                    eye_length_mm=float(face["eye_length_mm"]),
                    eye_tilt_mm=float(face["eye_tilt_mm"]),
                    eye_radius_mm=float(face["eye_radius_mm"]),
                    eye_blend_mm=float(face["eye_blend_mm"]),
                    muzzle_x_offset_mm=float(face["muzzle_x_offset_mm"]),
                    muzzle_center_y_mm=float(face["muzzle_center_y_mm"]),
                    muzzle_z_mm=float(face["muzzle_z_mm"]),
                    muzzle_radii_mm=_vector3(
                        face["muzzle_radii_mm"], "cat.face.muzzle_radii_mm"
                    ),
                    muzzle_blend_mm=float(face["muzzle_blend_mm"]),
                    nose_center=_vector3(face["nose_center"], "cat.face.nose_center"),
                    nose_radii_mm=_vector3(
                        face["nose_radii_mm"], "cat.face.nose_radii_mm"
                    ),
                    nose_blend_mm=float(face["nose_blend_mm"]),
                    mouth_center_y_mm=float(face["mouth_center_y_mm"]),
                    mouth_z_mm=float(face["mouth_z_mm"]),
                    mouth_half_width_mm=float(face["mouth_half_width_mm"]),
                    mouth_drop_mm=float(face["mouth_drop_mm"]),
                    mouth_radius_mm=float(face["mouth_radius_mm"]),
                    mouth_blend_mm=float(face["mouth_blend_mm"]),
                ),
            ),
        )
        specification.validate()
        return specification
