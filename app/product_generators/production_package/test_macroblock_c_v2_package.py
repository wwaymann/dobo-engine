from __future__ import annotations

from pathlib import Path

from product_generators.surface_designer.v2_prototype_1 import build_v2_prototype_1
from product_generators.surface_designer.v2_prototype_1_spec import V2Prototype1Parser

from .bundle import ProductionPackageBuilder
from .render_contract import RenderContract, RenderIntent


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "v2_prototype_1_dobo.json"
)


def main() -> None:
    specification = V2Prototype1Parser().parse_file(SPEC_PATH)
    generated = build_v2_prototype_1(specification)
    if generated.generation_seconds > generated.max_generation_seconds:
        raise RuntimeError("V2 prototype exceeded its generation budget.")

    contract = RenderContract.standard(RenderIntent.COMMERCIAL)
    builder = ProductionPackageBuilder()
    manifest = builder.build(
        source_specification=SPEC_PATH,
        motor_version="macroblock-c.C1",
        source_revision="macroblock-b:b9ceaddf89b31d0b9cbd50f07657dc56ad355d72",
        artifacts={
            "render_preview": generated.preview_path,
            "stl": generated.stl_path,
        },
        render_contract=contract,
        required_artifacts=("render_preview", "stl"),
    )

    if len(manifest.artifacts) != 2:
        raise RuntimeError("V2 package did not preserve STL + render evidence.")
    if {record.kind for record in manifest.artifacts} != {"render_preview", "stl"}:
        raise RuntimeError("V2 package artifact kinds changed unexpectedly.")
    if not all(record.size_bytes > 0 for record in manifest.artifacts):
        raise RuntimeError("V2 package contains an empty artifact.")

    output = Path(generated.stl_path).parent / "v2_prototype_1_production_package.json"
    written = Path(builder.write(manifest, output))
    if not written.is_file() or written.stat().st_size <= 0:
        raise RuntimeError("Integrated V2 package manifest was not created.")

    print("DOBO Macroblock C - V2 End-to-End Package C1")
    print("-----------------------------------")
    print("source JSON", SPEC_PATH.name, "OK")
    print("generated solid", generated.solid_count, "OK")
    print("generation seconds", f"{generated.generation_seconds:.3f}")
    print("STL", generated.stl_path, "OK")
    print("render", generated.preview_path, "OK")
    print("package artifacts", len(manifest.artifacts), "OK")
    print("package sha256", manifest.package_sha256)
    print("manifest", written)
    print("-----------------------------------")
    print("Macroblock C V2 Package C1: Valid OK")


if __name__ == "__main__":
    main()
