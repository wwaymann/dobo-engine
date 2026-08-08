from __future__ import annotations

from pathlib import Path

from .profile import ManufacturingProfile
from .runner import analyze_phase_6_product


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "phase_5_product_spec.json"
)


def main() -> None:
    result = analyze_phase_6_product(
        specification_path=SPEC_PATH,
        profile=ManufacturingProfile(
            nozzle_diameter=0.4,
            layer_height=0.20,
            min_wall_thickness=0.8,
            min_feature_size=0.45,
            min_color_region_volume=1.0,
            max_overhang_angle=50.0,
            min_bed_contact_area=25.0,
            min_clearance=0.25,
        ),
    )

    print(
        "DOBO Manufacturability - Phase 7.2\n"
        "Semantic Manufacturing Checks\n"
        "-----------------------------------"
    )

    for check in result.report.checks:
        suffix = ""

        if check.measured_value is not None:
            suffix += (
                " measured="
                f"{check.measured_value:.3f}"
            )

        if check.required_value is not None:
            suffix += (
                " required="
                f"{check.required_value:.3f}"
            )

        if check.unit is not None:
            suffix += f" {check.unit}"

        print(
            f"{check.label:<24} "
            f"{check.status.value:<8} "
            f"{check.code}"
            f"{suffix}"
        )

    print(
        "-----------------------------------"
    )
    print(
        "overall",
        result.report.overall_status.value,
    )
    print(
        "printable",
        result.report.printable,
    )

    if not result.report.printable:
        raise RuntimeError(
            "Phase 7.2 product failed "
            "semantic manufacturing validation."
        )

    print(
        "Phase 7.2 Semantic Manufacturing: Valid OK"
    )


if __name__ == "__main__":
    main()
