from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, pi, sin, sqrt
import unicodedata
from typing import Any

from .design_grammar import DesignGrammarPlan
from .semantic_contract import DesignSemanticProgram


TOPOLOGY_GRAPH_VERSION = "6A.2"
SECTION_PROFILE_VERSION = "6B.3"
STRUCTURAL_SYNTHESIS_VERSION = "6C.4"
MORPHOLOGY_ACCEPTANCE_VERSION = "6E.3"


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )


@dataclass(frozen=True, slots=True)
class StructuralMorphologyPlan:
    profile: str
    axis_mode: str
    section_count: int
    radial_repetitions: int
    bilateral_pairs: int

    def validate(self) -> None:
        if self.profile not in {
            "bilateral_mass",
            "radial_petal",
            "helical_chain",
            "axial_faceted",
            "spherical_mass",
        }:
            raise ValueError("Unknown structural morphology profile.")
        if self.axis_mode not in {"bilateral", "radial", "helical", "axial"}:
            raise ValueError("Unknown structural morphology axis mode.")
        if self.section_count < 3:
            raise ValueError("Structural morphology requires at least three sections.")
        if self.radial_repetitions < 0 or self.bilateral_pairs < 0:
            raise ValueError("Structural morphology group counts are invalid.")


class StructuralMorphogenesisResolver:
    """Resolve a global body topology from reusable semantic relationships."""

    @classmethod
    def resolve(
        cls,
        program: DesignSemanticProgram,
        grammar: DesignGrammarPlan,
    ) -> StructuralMorphologyPlan:
        tags = {_normalized(tag) for tag in program.body.style_tags}
        botanical = sum(
            feature.component_kind == "botanical_lobe"
            for feature in grammar.features
        )
        bilateral = sum(
            feature.mass_strategy == "silhouette_mass"
            and feature.shape_profile in {"pointed", "elongated", "round"}
            for feature in grammar.features
        ) // 2
        if grammar.body_profile == "faceted_proxy":
            result = StructuralMorphologyPlan(
                "axial_faceted", "axial", 3, 0, 0
            )
        elif grammar.body_profile == "spherical":
            # Spherical is already an accepted semantic/body capability. Keep it
            # spherical instead of routing it through the generic helical fallback.
            result = StructuralMorphologyPlan(
                "spherical_mass", "axial", 3, 0, 0
            )
        elif botanical >= 3:
            result = StructuralMorphologyPlan(
                "radial_petal", "radial", 3, botanical, 0
            )
        elif tags & {"flowing", "sculptural", "spiral", "twisted"}:
            result = StructuralMorphologyPlan(
                "helical_chain", "helical", 6, 0, 0
            )
        elif bilateral or grammar.body_profile == "character":
            result = StructuralMorphologyPlan(
                "bilateral_mass", "bilateral", 3, 0, max(1, bilateral)
            )
        else:
            result = StructuralMorphologyPlan(
                "helical_chain", "helical", 6, 0, 0
            )
        result.validate()
        return result


class StructuralBodySynthesizer:
    """Replace a canonical envelope with a multi-section structural body."""

    @classmethod
    def apply(
        cls,
        motor_program: dict[str, Any],
        program: DesignSemanticProgram,
        grammar: DesignGrammarPlan,
        plan: StructuralMorphologyPlan,
    ) -> tuple[str, ...]:
        fields, blend = {
            "bilateral_mass": cls._bilateral,
            "radial_petal": cls._radial,
            "helical_chain": cls._helical,
            "axial_faceted": cls._faceted,
            "spherical_mass": cls._spherical,
        }[plan.profile](program)
        old_body_ids = set(motor_program["composition"]["field_ids"])
        motor_program["fields"] = [
            field
            for field in motor_program["fields"]
            if field["id"] not in old_body_ids
        ] + fields
        ids = tuple(str(field["id"]) for field in fields)
        motor_program["composition"]["field_ids"] = list(ids)
        motor_program["vessel"]["shell_field_ids"] = list(ids)
        motor_program["composition"]["blend_mm"] = min(
            blend,
            max(grammar.style.fusion_mm, 4.0 * motor_program["grid"]["voxel_mm"]),
        )
        motor_program["morphogenesis"] = {
            "topology_version": TOPOLOGY_GRAPH_VERSION,
            "section_version": SECTION_PROFILE_VERSION,
            "synthesis_version": STRUCTURAL_SYNTHESIS_VERSION,
            "acceptance_version": MORPHOLOGY_ACCEPTANCE_VERSION,
            "profile": plan.profile,
            "axis_mode": plan.axis_mode,
            "section_count": plan.section_count,
            "field_ids": list(ids),
        }
        return ids

    @staticmethod
    def _advanced(
        field_id: str,
        center: list[float],
        radii: list[float],
        *,
        exponent: float = 2.6,
    ) -> dict[str, Any]:
        return {
            "id": field_id,
            "kind": "superellipsoid",
            "center": center,
            "radii": radii,
            "exponent": exponent,
            "round_mm": max(0.7, 0.035 * min(radii)),
        }

    @classmethod
    def _spherical(
        cls, program: DesignSemanticProgram
    ) -> tuple[list[dict[str, Any]], float]:
        """Preserve an accepted spherical body with existing superellipsoid fields.

        The three strongly-overlapping fields satisfy the structural multi-section
        contract without inventing a new primitive or deforming the requested body
        into a helical chain.  The primary field carries the actual sphere; the two
        subordinate fields remain fully embedded/overlapping so smooth union stays
        a single connected surface.
        """
        width = program.body.width_mm
        depth = program.body.depth_mm
        height = program.body.height_mm
        primary = [0.48 * width, 0.48 * depth, 0.48 * height]
        inner = [0.43 * width, 0.43 * depth, 0.43 * height]
        return [
            cls._advanced(
                "body",
                [0.0, 0.0, 0.0],
                primary,
                exponent=2.0,
            ),
            cls._advanced(
                "front_mass",
                [0.0, -0.01 * depth, 0.0],
                [0.46 * width, 0.46 * depth, 0.46 * height],
                exponent=2.0,
            ),
            cls._advanced(
                "body_bridge",
                [0.0, 0.0, 0.0],
                inner,
                exponent=2.0,
            ),
        ], 3.6

    @classmethod
    def _bilateral(
        cls, program: DesignSemanticProgram
    ) -> tuple[list[dict[str, Any]], float]:
        width = program.body.width_mm
        depth = program.body.depth_mm
        height = program.body.height_mm
        return [
            cls._advanced(
                "body",
                [0.0, 0.04 * depth, -0.18 * height],
                [0.48 * width, 0.46 * depth, 0.34 * height],
                exponent=2.35,
            ),
            cls._advanced(
                "front_mass",
                [0.0, -0.05 * depth, 0.20 * height],
                [0.43 * width, 0.40 * depth, 0.28 * height],
                exponent=2.55,
            ),
            cls._advanced(
                "body_bridge",
                [0.0, -0.06 * depth, 0.01 * height],
                [0.33 * width, 0.34 * depth, 0.24 * height],
                exponent=2.25,
            ),
        ], 3.8

    @classmethod
    def _radial(
        cls, program: DesignSemanticProgram
    ) -> tuple[list[dict[str, Any]], float]:
        width = program.body.width_mm
        depth = program.body.depth_mm
        height = program.body.height_mm
        fields = [
            cls._advanced(
                "body",
                [0.0, 0.0, -0.04 * height],
                [0.35 * width, 0.35 * depth, 0.48 * height],
                exponent=2.8,
            )
        ]
        for index in range(6):
            angle = 2.0 * pi * index / 6.0
            radial_x = abs(sin(angle))
            radial_y = abs(cos(angle))
            fields.append(
                cls._advanced(
                    "front_mass" if index == 0 else f"radial_body_{index}",
                    [
                        0.20 * width * sin(angle),
                        -0.20 * depth * cos(angle),
                        -0.06 * height,
                    ],
                    [
                        (0.18 + 0.11 * radial_x) * width,
                        (0.18 + 0.11 * radial_y) * depth,
                        0.43 * height,
                    ],
                    exponent=2.5,
                )
            )
        return fields, 3.4

    @classmethod
    def _helical(
        cls, program: DesignSemanticProgram
    ) -> tuple[list[dict[str, Any]], float]:
        width = program.body.width_mm
        depth = program.body.depth_mm
        height = program.body.height_mm
        fields: list[dict[str, Any]] = []
        for index in range(6):
            ratio = index / 5.0
            angle = radians_value = (-55.0 + 250.0 * ratio) * pi / 180.0
            field_id = "body" if index == 0 else (
                "front_mass" if index == 1 else f"helical_body_{index}"
            )
            fields.append(
                cls._advanced(
                    field_id,
                    [
                        0.11 * width * sin(angle),
                        0.11 * depth * cos(radians_value),
                        (-0.31 + 0.124 * index) * height,
                    ],
                    [0.34 * width, 0.30 * depth, 0.19 * height],
                    exponent=2.45 + 0.12 * (index % 2),
                )
            )
        return fields, 4.0

    @staticmethod
    def _faceted(
        program: DesignSemanticProgram,
    ) -> tuple[list[dict[str, Any]], float]:
        width = program.body.width_mm
        depth = program.body.depth_mm
        height = program.body.height_mm

        def field(
            field_id: str,
            center_z: float,
            radial: float,
            axial: float,
            rotation: float,
        ) -> dict[str, Any]:
            return {
                "id": field_id,
                "kind": "faceted_ellipsoid",
                "center": [0.0, 0.0, center_z * height],
                "radii": [radial * width, radial * depth, axial * height],
                "exponent": 4.0,
                "sides": 6,
                "rotation_degrees": rotation,
                "round_mm": 1.0,
            }

        return [
            field("body", -0.27, 0.40, 0.25, 30.0),
            field("front_mass", -0.01, 0.50, 0.30, 0.0),
            field("faceted_upper", 0.28, 0.41, 0.25, 30.0),
        ], 3.0


def _scalar_field_distance(
    field: dict[str, Any], x: float, y: float, z: float
) -> float:
    center = tuple(float(value) for value in field["center"])
    radii = tuple(float(value) for value in field["radii"])
    px = x - center[0]
    py = y - center[1]
    pz = z - center[2]
    kind = str(field.get("kind", "ellipsoid"))
    if kind == "ellipsoid":
        k0 = sqrt(
            (px / radii[0]) ** 2
            + (py / radii[1]) ** 2
            + (pz / radii[2]) ** 2
        )
        k1 = sqrt(
            (px / radii[0] ** 2) ** 2
            + (py / radii[1] ** 2) ** 2
            + (pz / radii[2] ** 2) ** 2
        )
        return k0 * (k0 - 1.0) / k1 if k1 > 1e-12 else -min(radii)
    exponent = float(field.get("exponent", 2.0))
    if kind == "faceted_ellipsoid":
        normalized_x = px / radii[0]
        normalized_y = py / radii[1]
        angle = atan2(normalized_y, normalized_x) - (
            float(field.get("rotation_degrees", 0.0)) * pi / 180.0
        )
        sides = int(field.get("sides", 6))
        sector = 2.0 * pi / sides
        local = (angle + 0.5 * sector) % sector - 0.5 * sector
        polygon_radius = cos(0.5 * sector) / cos(local)
        radial = sqrt(normalized_x**2 + normalized_y**2) / polygon_radius
        normalized = (
            radial**exponent + abs(pz / radii[2]) ** exponent
        ) ** (1.0 / exponent)
    else:
        normalized = (
            abs(px / radii[0]) ** exponent
            + abs(py / radii[1]) ** exponent
            + abs(pz / radii[2]) ** exponent
        ) ** (1.0 / exponent)
    return (normalized - 1.0) * min(radii)


def front_surface_y(
    motor_program: dict[str, Any], *, x: float, z: float
) -> float:
    """Resolve the first front-facing zero crossing of the hollow body field."""
    fields = {str(field["id"]): field for field in motor_program["fields"]}
    body_ids = tuple(motor_program["vessel"].get("shell_field_ids", ()))
    if not body_ids:
        body_ids = tuple(motor_program["morphogenesis"]["field_ids"])
    blend = float(motor_program["composition"]["blend_mm"])

    def sample(y: float) -> float:
        value = _scalar_field_distance(fields[body_ids[0]], x, y, z)
        for field_id in body_ids[1:]:
            other = _scalar_field_distance(fields[field_id], x, y, z)
            mix = min(1.0, max(0.0, 0.5 + 0.5 * (other - value) / blend))
            value = (
                other * (1.0 - mix)
                + value * mix
                - blend * mix * (1.0 - mix)
            )
        return value

    minimum_y = float(motor_program["grid"]["minimum"][1])
    maximum_y = float(motor_program["grid"]["maximum"][1])
    outside_y = minimum_y
    outside_value = sample(outside_y)
    steps = 256
    for index in range(1, steps + 1):
        inside_y = minimum_y + (maximum_y - minimum_y) * index / steps
        inside_value = sample(inside_y)
        if outside_value > 0.0 and inside_value <= 0.0:
            for _ in range(32):
                middle = 0.5 * (outside_y + inside_y)
                if sample(middle) > 0.0:
                    outside_y = middle
                else:
                    inside_y = middle
            return 0.5 * (outside_y + inside_y)
        outside_y = inside_y
        outside_value = inside_value
    raise RuntimeError("Morphogenesis body has no front surface at the requested anchor.")
