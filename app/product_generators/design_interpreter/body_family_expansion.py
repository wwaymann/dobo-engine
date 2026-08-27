from __future__ import annotations

from dataclasses import dataclass
import unicodedata
from typing import Any

from .semantic_contract import DesignSemanticProgram


BODY_FAMILY_EXPANSION_VERSION = "B28.6"


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).replace("-", "_").replace(" ", "_")


@dataclass(frozen=True, slots=True)
class BodyFamilyExpansionResult:
    applied: bool
    profile: str
    field_ids: tuple[str, ...]


class GeneralBodyFamilyExpander:
    """Expand reusable planter base families without product-specific branches."""

    _PROFILE_TAGS = (
        ("tapered_revolution", {"tapered", "tapered_revolution", "truncated_cone", "conical", "frustum"}),
        ("rectangular_prism", {"rectangular", "rectangular_prism", "elongated_planter", "oblong"}),
        ("cuboid", {"cuboid", "cubic", "cube", "architectural_cube", "boxy"}),
        ("triangular_prism", {"triangular", "triangular_prism", "triangle_prism"}),
        ("ovoid", {"ovoid", "egg", "ellipsoidal", "bulbous"}),
        ("cylindrical", {"cylindrical", "cylinder", "straight_cylinder"}),
        ("compound_multivolume", {"compound_multivolume", "multivolume", "multi_volume", "compound_body"}),
    )

    @classmethod
    def requested_profile(cls, program: DesignSemanticProgram) -> str | None:
        tags = {_normalized(tag) for tag in program.body.style_tags}
        tags.add(_normalized(program.body.family))
        for profile, aliases in cls._PROFILE_TAGS:
            if tags & aliases:
                return profile
        return None

    @staticmethod
    def _superellipsoid(field_id: str, center: list[float], radii: list[float], *, exponent: float, round_mm: float) -> dict[str, Any]:
        return {"id": field_id, "kind": "superellipsoid", "center": center, "radii": radii, "exponent": exponent, "round_mm": round_mm}

    @staticmethod
    def _faceted(field_id: str, center: list[float], radii: list[float], *, sides: int, exponent: float, round_mm: float, rotation_degrees: float = 0.0) -> dict[str, Any]:
        return {
            "id": field_id,
            "kind": "faceted_ellipsoid",
            "center": center,
            "radii": radii,
            "exponent": exponent,
            "sides": sides,
            "rotation_degrees": rotation_degrees,
            "round_mm": round_mm,
        }

    @staticmethod
    def _cylinder(field_id: str, center: list[float], *, radius: float, half_height: float) -> dict[str, Any]:
        return {
            "id": field_id,
            "kind": "capped_cylinder",
            "center": center,
            "radii": [radius, radius, half_height],
            "exponent": 2.0,
            "sides": 6,
            "round_mm": min(0.6, 0.25 * radius, 0.25 * half_height),
        }

    @classmethod
    def _fields_for(cls, profile: str, program: DesignSemanticProgram) -> tuple[list[dict[str, Any]], float]:
        width = float(program.body.width_mm)
        depth = float(program.body.depth_mm)
        height = float(program.body.height_mm)
        minimum = min(width, depth, height)

        if profile == "cylindrical":
            radius = 0.49 * min(width, depth)
            fields = [
                cls._cylinder("body", [0.0, 0.0, 0.0], radius=radius, half_height=0.47 * height),
                cls._cylinder("cylindrical_support", [0.0, 0.0, 0.0], radius=0.985 * radius, half_height=0.985 * 0.47 * height),
            ]
            return fields, max(0.8, minimum * 0.010)

        if profile == "tapered_revolution":
            fields: list[dict[str, Any]] = []
            for index, (z, radius, axial) in enumerate(((-0.31, 0.31, 0.20), (-0.12, 0.35, 0.20), (0.09, 0.40, 0.21), (0.29, 0.45, 0.19))):
                fields.append(cls._superellipsoid("body" if index == 0 else f"tapered_body_{index}", [0.0, 0.0, z * height], [radius * width, radius * depth, axial * height], exponent=2.45, round_mm=max(0.8, minimum * 0.012)))
            return fields, max(2.4, minimum * 0.030)

        if profile == "cuboid":
            fields = [
                cls._superellipsoid("body", [0.0, 0.0, -0.25 * height], [0.49 * width, 0.49 * depth, 0.29 * height], exponent=7.0, round_mm=max(1.0, minimum * 0.015)),
                cls._superellipsoid("cuboid_mid", [0.0, 0.0, 0.0], [0.49 * width, 0.49 * depth, 0.29 * height], exponent=7.5, round_mm=max(1.0, minimum * 0.015)),
                cls._superellipsoid("cuboid_upper", [0.0, 0.0, 0.25 * height], [0.49 * width, 0.49 * depth, 0.29 * height], exponent=7.0, round_mm=max(1.0, minimum * 0.015)),
            ]
            return fields, max(2.4, minimum * 0.028)

        if profile == "rectangular_prism":
            fields = [
                cls._superellipsoid("body", [0.0, 0.0, -0.25 * height], [0.48 * width, 0.47 * depth, 0.29 * height], exponent=7.2, round_mm=max(1.0, minimum * 0.015)),
                cls._superellipsoid("rectangular_mid", [0.0, 0.0, 0.0], [0.49 * width, 0.48 * depth, 0.29 * height], exponent=7.8, round_mm=max(1.0, minimum * 0.015)),
                cls._superellipsoid("rectangular_upper", [0.0, 0.0, 0.25 * height], [0.48 * width, 0.47 * depth, 0.29 * height], exponent=7.2, round_mm=max(1.0, minimum * 0.015)),
            ]
            return fields, max(2.4, minimum * 0.028)

        if profile == "triangular_prism":
            fields = [
                cls._faceted("body", [0.0, 0.0, -0.25 * height], [0.48 * width, 0.48 * depth, 0.27 * height], sides=3, exponent=7.5, round_mm=max(0.8, minimum * 0.012), rotation_degrees=30.0),
                cls._faceted("triangular_mid", [0.0, 0.0, 0.0], [0.49 * width, 0.49 * depth, 0.26 * height], sides=3, exponent=8.0, round_mm=max(0.8, minimum * 0.012), rotation_degrees=30.0),
                cls._faceted("triangular_upper", [0.0, 0.0, 0.25 * height], [0.48 * width, 0.48 * depth, 0.27 * height], sides=3, exponent=7.5, round_mm=max(0.8, minimum * 0.012), rotation_degrees=30.0),
            ]
            return fields, max(1.8, minimum * 0.020)

        if profile == "ovoid":
            fields = [
                cls._superellipsoid("body", [0.0, 0.0, -0.20 * height], [0.39 * width, 0.39 * depth, 0.34 * height], exponent=2.15, round_mm=max(1.0, minimum * 0.018)),
                cls._superellipsoid("ovoid_belly", [0.0, 0.0, 0.02 * height], [0.49 * width, 0.48 * depth, 0.34 * height], exponent=2.05, round_mm=max(1.0, minimum * 0.018)),
                cls._superellipsoid("ovoid_upper", [0.0, 0.0, 0.28 * height], [0.39 * width, 0.38 * depth, 0.22 * height], exponent=2.15, round_mm=max(1.0, minimum * 0.018)),
            ]
            return fields, max(3.0, minimum * 0.032)

        if profile == "compound_multivolume":
            fields = [
                cls._superellipsoid("body", [0.0, 0.0, -0.42 * height], [0.40 * width, 0.38 * depth, 0.15 * height], exponent=4.5, round_mm=max(1.0, minimum * 0.014)),
                cls._superellipsoid("compound_left", [-0.18 * width, 0.02 * depth, -0.12 * height], [0.34 * width, 0.39 * depth, 0.42 * height], exponent=2.5, round_mm=max(1.0, minimum * 0.016)),
                cls._superellipsoid("compound_right", [0.22 * width, -0.03 * depth, 0.03 * height], [0.34 * width, 0.36 * depth, 0.34 * height], exponent=2.65, round_mm=max(1.0, minimum * 0.016)),
                cls._superellipsoid("compound_upper", [0.02 * width, 0.03 * depth, 0.27 * height], [0.31 * width, 0.33 * depth, 0.23 * height], exponent=2.45, round_mm=max(1.0, minimum * 0.016)),
                cls._superellipsoid("compound_bridge", [0.02 * width, 0.0, -0.01 * height], [0.28 * width, 0.31 * depth, 0.31 * height], exponent=2.25, round_mm=max(1.0, minimum * 0.016)),
            ]
            return fields, max(3.4, minimum * 0.036)

        raise ValueError(f"Unsupported body family expansion profile: {profile!r}")

    @classmethod
    def apply(cls, motor_program: dict[str, Any], program: DesignSemanticProgram) -> BodyFamilyExpansionResult:
        profile = cls.requested_profile(program)
        if profile is None:
            current = motor_program.get("morphogenesis", {})
            return BodyFamilyExpansionResult(False, str(current.get("profile", "unknown")), tuple(str(item) for item in current.get("field_ids", ())))

        fields, blend = cls._fields_for(profile, program)
        morphology = motor_program.setdefault("morphogenesis", {})
        old_ids = {str(item) for item in morphology.get("field_ids", ())}
        new_ids = tuple(str(field["id"]) for field in fields)
        motor_program["fields"] = [field for field in motor_program["fields"] if str(field.get("id")) not in old_ids] + fields
        composition_ids = [str(item) for item in motor_program["composition"].get("field_ids", ()) if str(item) not in old_ids]
        motor_program["composition"]["field_ids"] = list(new_ids) + composition_ids
        motor_program["composition"]["blend_mm"] = float(blend)
        motor_program["vessel"]["shell_field_ids"] = list(new_ids)
        morphology.update({"capability_version": BODY_FAMILY_EXPANSION_VERSION, "profile": profile, "axis_mode": "axial" if profile != "compound_multivolume" else "compound", "field_ids": list(new_ids), "section_count": len(new_ids)})
        return BodyFamilyExpansionResult(True, profile, new_ids)
