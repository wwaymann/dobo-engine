from __future__ import annotations

from pathlib import Path
from .composition_spec import ProductCompositionParser
from .json_product_composer import JsonProductComposer

SPEC_PATH = Path(__file__).resolve().parent / "phase_5_product_spec.json"


def build_json_product():
    specification = ProductCompositionParser().parse_file(SPEC_PATH)
    result = JsonProductComposer().compose(specification)
    print("DOBO Surface Designer - Phase 5")
    print("JSON Product Composition")
    print("-----------------------------------")
    print("id", specification.id)
    print("operations", " -> ".join(result.operations))
    print("solids", result.solids)
    print("faces", result.faces)
    print("volume", round(result.volume_final, 6))
    print("STEP", result.path)
    print("-----------------------------------")
    print("Phase 5 JSON Product Composition: Valid OK")
    return result


if __name__ == "__main__":
    build_json_product()
