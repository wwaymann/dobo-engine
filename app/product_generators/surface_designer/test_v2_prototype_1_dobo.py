from __future__ import annotations

from pathlib import Path

from .v2_prototype_1 import build_v2_prototype_1
from .v2_prototype_1_spec import V2Prototype1Parser


SPEC_PATH = Path(__file__).resolve().parent / "v2_prototype_1_dobo.json"


def main() -> None:
    specification = V2Prototype1Parser().parse_file(SPEC_PATH)
    expected_texts = ["Dobo", "Planta una idea"]
    actual_texts = [item.content for item in specification.texts]
    if actual_texts != expected_texts:
        raise RuntimeError(
            f"Unexpected prototype texts: {actual_texts}; expected {expected_texts}."
        )
    if specification.manufacturing.colors != 1:
        raise RuntimeError("Prototype 1 must be monochromatic.")

    result = build_v2_prototype_1(specification)
    if result.product_id != specification.id:
        raise RuntimeError("Result did not preserve the JSON product id.")
    if not result.shape.isValid() or result.solid_count != 1:
        raise RuntimeError("Prototype 1 must be one valid connected solid.")
    if result.volume <= 0.0 or result.triangle_count <= 0:
        raise RuntimeError("Prototype 1 has no measurable geometry.")

    print("DOBO V2 Prototype 1 - Monochrome")
    print("JSON -> planter -> texts -> STL/render")
    print("-----------------------------------")
    print("specification", specification.id, "OK")
    print("texts", len(specification.texts), "from JSON", "OK")
    print("colors", specification.manufacturing.colors, "OK")
    print("connected final product", "OK")
    print("triangles", result.triangle_count)
    print("stage timings")
    for name, seconds in result.stage_seconds.items():
        print(" ", name, f"{seconds:.3f}s")
    print("generation seconds", f"{result.generation_seconds:.3f}")
    print("generation target", result.max_generation_seconds, "seconds")
    print("STL", result.stl_path)
    print("render", result.preview_path)
    print("-----------------------------------")

    if result.generation_seconds > result.max_generation_seconds:
        raise RuntimeError(
            "V2 generation budget exceeded: "
            f"{result.generation_seconds:.3f}s > "
            f"{result.max_generation_seconds:.3f}s. "
            f"Stages: {result.stage_seconds}"
        )

    print("generation budget", "OK")
    print("DOBO V2 Prototype 1: Valid OK")


if __name__ == "__main__":
    main()
