from __future__ import annotations

from pathlib import Path

from product_generators.surface_designer.multicolor_product import build_multicolor_product

from .final_geometry import FinalGeometryManufacturingAnalyzer
from .production_orientation import ProductionOrientationPlanner
from .profile import ManufacturingProfile


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "phase_5_product_spec.json"
)


def main() -> None:
    profile = ManufacturingProfile()
    product = build_multicolor_product(SPEC_PATH)
    planner = ProductionOrientationPlanner()
    plan = planner.plan(shape=product.final_shape, profile=profile)
    analyzer = FinalGeometryManufacturingAnalyzer()
    label = plan.selected.label
    tolerance = max(profile.bed_z_tolerance, profile.layer_height)

    print("DOBO Macroblock B - Real Overhang Source Diagnostics")
    print("-----------------------------------")
    print("selected", label)
    print("candidate count", len(plan.candidates))
    print("selected planner angle", round(plan.selected.overhang_angle, 4))
    print("selected planner valid", plan.selected.overhang_valid)

    sources = {
        "FINAL": product.final_shape,
        "BODY": product.body_region,
        "TEXT": product.text_region,
        "DECORATION": product.decoration_region,
    }
    for name, source in sources.items():
        oriented = planner._oriented_shape(source, label)
        result = analyzer.overhang(
            shape=oriented,
            maximum_allowed_angle=profile.max_overhang_angle,
            bed_tolerance=tolerance,
        )
        print(
            name,
            "angle",
            round(float(result.maximum_overhang_angle or 0.0), 4),
            "valid",
            result.valid,
            "triangles",
            result.sampled_triangles,
        )

    ranked = sorted(plan.candidates, key=lambda item: item.ranking_key)[:8]
    print("best candidates")
    for item in ranked:
        print(
            item.label,
            "angle",
            round(item.overhang_angle, 4),
            "size_valid",
            item.size_valid,
            "overhang_valid",
            item.overhang_valid,
        )
    print("-----------------------------------")
    print("Macroblock B Real Overhang Source Diagnostics: Complete")


if __name__ == "__main__":
    main()
