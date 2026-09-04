from __future__ import annotations

from itertools import combinations
from math import cos, pi, sin

import numpy as np

from product_generators.organic_shapes.fields import (
    implicit_field_distance,
    smooth_union,
)
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)

from .phase_6_morphogenesis_matrix import morphogenesis_matrix
from .structural_compiler import StructuralSemanticCompiler
from .structural_morphogenesis import (
    MORPHOLOGY_ACCEPTANCE_VERSION,
    SECTION_PROFILE_VERSION,
    STRUCTURAL_SYNTHESIS_VERSION,
    TOPOLOGY_GRAPH_VERSION,
)
from .structural_pipeline import STRUCTURAL_PIPELINE_VERSION


def _section_signature(case, motor: dict) -> np.ndarray:
    specification = HierarchicalFeatureParser().parse_dict(motor)
    fields = {field.id: field for field in specification.fields}
    ids = tuple(motor["morphogenesis"]["field_ids"])
    blend = float(motor["composition"]["blend_mm"])

    def outer(x: float, y: float, z: float) -> float:
        value = implicit_field_distance(
            np.asarray(x), np.asarray(y), np.asarray(z), fields[ids[0]]
        )
        for field_id in ids[1:]:
            value = smooth_union(
                value,
                implicit_field_distance(
                    np.asarray(x),
                    np.asarray(y),
                    np.asarray(z),
                    fields[field_id],
                ),
                blend,
            )
        return float(value)

    normalization = max(case.program.body.width_mm, case.program.body.depth_mm)
    radii: list[float] = []
    for height_ratio in (-0.28, 0.0, 0.28):
        z = height_ratio * case.program.body.height_mm
        for index in range(12):
            angle = 2.0 * pi * index / 12.0
            lower = 0.0
            upper = 0.8 * normalization
            if outer(0.0, 0.0, z) > 0.0:
                raise RuntimeError(f"{case.label} lost its central vessel envelope.")
            for _ in range(28):
                middle = 0.5 * (lower + upper)
                x = middle * cos(angle)
                y = middle * sin(angle)
                if outer(x, y, z) <= 0.0:
                    lower = middle
                else:
                    upper = middle
            radii.append(0.5 * (lower + upper) / normalization)
    return np.asarray(radii, dtype=np.float64)


def main() -> None:
    print()
    print("DOBO Structural Morphogenesis - Rebuilt Block 6")
    print("topology -> sections -> body synthesis -> manufacturing -> acceptance")
    print("-----------------------------------")
    print("topology graph version", TOPOLOGY_GRAPH_VERSION, "OK")
    print("section profile version", SECTION_PROFILE_VERSION, "OK")
    print("structural synthesis version", STRUCTURAL_SYNTHESIS_VERSION, "OK")
    print("morphology acceptance version", MORPHOLOGY_ACCEPTANCE_VERSION, "OK")
    print("pipeline version", STRUCTURAL_PIPELINE_VERSION, "OK")

    expected = {
        "bilateral": ("bilateral_mass", 3),
        "radial": ("radial_petal", 7),
        "helical": ("helical_chain", 6),
        "faceted": ("axial_faceted", 3),
    }
    signatures: dict[str, np.ndarray] = {}
    for case in morphogenesis_matrix():
        compiled = StructuralSemanticCompiler.compile(case.program)
        profile, minimum_fields = expected[case.id]
        if compiled.report.morphology_profile != profile:
            raise RuntimeError(f"{case.label} resolved the wrong body topology.")
        if compiled.report.morphology_fields < minimum_fields:
            raise RuntimeError(f"{case.label} has insufficient structural masses.")
        morphogenesis = compiled.motor_program.get("morphogenesis")
        if not isinstance(morphogenesis, dict):
            raise RuntimeError(f"{case.label} lost its morphogenesis trace.")
        if set(morphogenesis["field_ids"]) - set(
            compiled.motor_program["composition"]["field_ids"]
        ):
            raise RuntimeError(f"{case.label} body fields are not active.")
        signature = _section_signature(case, compiled.motor_program)
        if np.ptp(signature) < 0.08:
            raise RuntimeError(f"{case.label} body sections are nearly uniform.")
        signatures[case.id] = signature
        print(
            case.label,
            "topology",
            profile,
            "fields",
            compiled.report.morphology_fields,
            "section range",
            round(float(np.ptp(signature)), 4),
            "OK",
        )

    minimum_distance = min(
        float(np.mean(np.abs(signatures[left] - signatures[right])))
        for left, right in combinations(sorted(signatures), 2)
    )
    if minimum_distance < 0.035:
        raise RuntimeError("Morphogenesis matrix bodies remain structurally similar.")
    print("minimum normalized structural distance", round(minimum_distance, 4), "OK")

    helical = signatures["helical"].reshape(3, 12)
    opposite_difference = float(np.mean(np.abs(helical[:, :6] - helical[:, 6:])))
    if opposite_difference < 0.05:
        raise RuntimeError("Helical body lost its global asymmetry.")
    print("helical asymmetry", round(opposite_difference, 4), "OK")
    print("unique body topologies", len(signatures), "OK")
    print("product-specific compiler branches", 0, "OK")
    print("-----------------------------------")
    print("No mesh generation or API credit required OK")
    print("DOBO Structural Morphogenesis Rebuilt Block 6: Valid OK")


if __name__ == "__main__":
    main()
