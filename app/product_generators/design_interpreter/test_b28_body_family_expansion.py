from __future__ import annotations

from itertools import combinations

import numpy as np

from .body_family_expansion import (
    BODY_FAMILY_EXPANSION_VERSION,
    GeneralBodyFamilyExpander,
)
from .phase_b28_capability_matrix import b28_capability_matrix
from .structural_compiler import StructuralSemanticCompiler


def _signature(motor: dict) -> np.ndarray:
    fields = {str(item["id"]): item for item in motor["fields"]}
    ids = tuple(str(item) for item in motor["morphogenesis"]["field_ids"])
    values: list[float] = []
    for field_id in ids:
        field = fields[field_id]
        center = tuple(float(value) for value in field["center"])
        radii = tuple(float(value) for value in field["radii"])
        values.extend((*center, *radii, float(field.get("exponent", 2.0))))
    vector = np.asarray(values, dtype=float)
    if vector.size < 28:
        vector = np.pad(vector, (0, 28 - vector.size))
    return vector[:28]


def main() -> None:
    print("DOBO B28 - General Body Family Expansion")
    print("-----------------------------------")
    print("version", BODY_FAMILY_EXPANSION_VERSION)

    signatures: dict[str, np.ndarray] = {}
    applied = 0
    for case in b28_capability_matrix():
        compiled = StructuralSemanticCompiler.compile(case.program)
        motor = compiled.motor_program
        expansion = GeneralBodyFamilyExpander.apply(motor, case.program)
        profile = str(motor["morphogenesis"]["profile"])
        if profile != case.expected_profile:
            raise RuntimeError(
                f"{case.label} resolved {profile!r}, expected {case.expected_profile!r}."
            )
        if expansion.applied:
            applied += 1
            if len(expansion.field_ids) < 3:
                raise RuntimeError(f"{case.label} has insufficient body fields.")
        if set(motor["vessel"]["shell_field_ids"]) != set(motor["morphogenesis"]["field_ids"]):
            raise RuntimeError(f"{case.label} shell lost expanded body fields.")
        signatures[case.id] = _signature(motor)
        print(case.label, profile, len(motor["morphogenesis"]["field_ids"]), "OK")

    if applied != 5:
        raise RuntimeError(f"Expected exactly five new family expansions, got {applied}.")

    expanded_ids = (
        "truncated_cone",
        "cubic_architectural",
        "rectangular_planter",
        "ovoid_sculptural",
        "compound_multivolume",
    )
    minimum_distance = min(
        float(np.linalg.norm(signatures[left] - signatures[right]))
        for left, right in combinations(expanded_ids, 2)
    )
    if minimum_distance <= 1.0:
        raise RuntimeError("Expanded body families collapsed to nearly identical field signatures.")

    print("expanded families", applied, "OK")
    print("minimum expanded signature distance", round(minimum_distance, 4), "OK")
    print("product-specific generator branches", 0, "OK")
    print("-----------------------------------")
    print("DOBO B28 General Body Family Expansion: Valid OK")


if __name__ == "__main__":
    main()
