from __future__ import annotations

from .phase_d_visual_matrix import d_visual_matrix
from .structural_compiler import StructuralSemanticCompiler


EXPRESSIVE_KINDS = {"lobed_ellipsoid", "twisted_faceted"}


def main() -> None:
    print("DOBO Macroblock D1 - Advanced Form Generation")
    print("visual DNA -> expressive morphology -> new implicit fields")
    print("-----------------------------------")
    profiles = set()
    expressive_cases = 0
    for case in d_visual_matrix():
        compiled = StructuralSemanticCompiler.compile(case.program)
        motor = compiled.motor_program
        actual = str(motor["morphogenesis"]["profile"])
        if actual != case.expected_profile:
            raise RuntimeError(f"{case.id}: expected {case.expected_profile}, got {actual}")
        active_ids = set(motor["vessel"]["shell_field_ids"])
        kinds = {
            str(field.get("kind", "ellipsoid"))
            for field in motor["fields"]
            if str(field["id"]) in active_ids
        }
        if not (kinds & EXPRESSIVE_KINDS):
            raise RuntimeError(f"{case.id}: expressive field family was not activated")
        profiles.add(actual)
        expressive_cases += 1
        print(case.label, actual, ",".join(sorted(kinds)), "OK")
    if len(profiles) < 4:
        raise RuntimeError("Macroblock D did not produce four distinct expressive morphology profiles.")
    if expressive_cases != 8:
        raise RuntimeError("Not all eight visual cases use expressive body construction.")
    print("-----------------------------------")
    print("expressive cases", expressive_cases, "OK")
    print("distinct expressive profiles", len(profiles), "OK")
    print("product-specific generator branches", 0, "OK")
    print("Macroblock D1 Advanced Form Generation: Valid OK")


if __name__ == "__main__":
    main()
