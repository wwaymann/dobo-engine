from __future__ import annotations

from pathlib import Path

from product_generators.surface_designer.multicolor_product import (
    build_multicolor_product,
)

from .product_integration import _exported_placement_is_on_bed
from .profile import ManufacturingProfile
from .three_mf_project_inspector import ThreeMFProjectInspector


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "phase_5_product_spec.json"
)


def main() -> None:
    profile = ManufacturingProfile()
    profile.validate()

    product = build_multicolor_product(SPEC_PATH)
    inspection = ThreeMFProjectInspector().inspect(product.three_mf_path)

    if not inspection.valid:
        raise RuntimeError("Real exported 3MF must preserve compound integrity.")
    if inspection.build_transform is None:
        raise RuntimeError("Real exported 3MF must expose a valid build transform.")
    if inspection.transformed_bounds is None:
        raise RuntimeError("Real exported 3MF must expose transformed mesh bounds.")
    if not _exported_placement_is_on_bed(
        bounds=inspection.transformed_bounds,
        profile=profile,
    ):
        raise RuntimeError("Real exported 3MF is not physically placed on the bed.")

    xmin, xmax, ymin, ymax, zmin, zmax = inspection.transformed_bounds

    # Negative guards prove ORIENTATION_ON_BED is no longer equivalent to
    # merely having one build item.
    shifted_above_bed = (xmin, xmax, ymin, ymax, zmin + 5.0, zmax + 5.0)
    if _exported_placement_is_on_bed(bounds=shifted_above_bed, profile=profile):
        raise RuntimeError("A model floating above the bed must be rejected.")

    shifted_outside_x = (
        xmin + profile.max_size_x,
        xmax + profile.max_size_x,
        ymin,
        ymax,
        zmin,
        zmax,
    )
    if _exported_placement_is_on_bed(bounds=shifted_outside_x, profile=profile):
        raise RuntimeError("A model outside the physical bed must be rejected.")

    print("DOBO Macroblock B - Real 3MF Placement")
    print("build transform", inspection.build_transform)
    print("transformed bounds", tuple(round(value, 4) for value in inspection.transformed_bounds))
    print("on bed", True)
    print("floating negative guard", "OK")
    print("outside-bed negative guard", "OK")
    print("Macroblock B Real 3MF Placement: Valid OK")


if __name__ == "__main__":
    main()
