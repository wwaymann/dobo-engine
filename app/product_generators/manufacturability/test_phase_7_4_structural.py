from __future__ import annotations

from pathlib import Path

import cadquery as cq

from .local_thickness import LocalThicknessAnalyzer
from .product_profile import ProductManufacturingProfile
from .profile import ManufacturingProfile
from .source import build_structural_body_source
from .stability import BaseStabilityAnalyzer
from .structural import StructuralBodyValidator


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "phase_5_product_spec.json"
)


def _fixture_wall(
    wall: float,
) -> cq.Shape:
    outer = (
        cq.Workplane("XY")
        .box(
            20.0,
            20.0,
            20.0,
            centered=(True, True, False),
        )
    )

    inner = (
        cq.Workplane("XY")
        .workplane(offset=wall)
        .box(
            20.0 - 2.0 * wall,
            20.0 - 2.0 * wall,
            20.0 - wall,
            centered=(True, True, False),
        )
    )

    return (
        outer
        .cut(inner)
        .val()
        .clean()
    )


def _validate_thickness_regression() -> None:
    analyzer = LocalThicknessAnalyzer()

    thin = analyzer.analyze(
        shape=_fixture_wall(0.4),
        threshold=0.8,
        samples_per_axis=3,
    )

    thick = analyzer.analyze(
        shape=_fixture_wall(2.0),
        threshold=0.8,
        samples_per_axis=3,
    )

    if (
        thin.minimum is None
        or not (0.35 <= thin.minimum <= 0.45)
    ):
        raise RuntimeError(
            f"Thin fixture regression failed: {thin.minimum}"
        )

    if (
        thick.minimum is None
        or not (1.90 <= thick.minimum <= 2.10)
    ):
        raise RuntimeError(
            f"Thick fixture regression failed: {thick.minimum}"
        )

    print(
        "wall fixtures",
        f"thin={thin.minimum:.3f}",
        f"thick={thick.minimum:.3f}",
        "OK",
    )


def _validate_stability_regression() -> None:
    centered = (
        cq.Workplane("XY")
        .box(
            40.0,
            40.0,
            20.0,
            centered=(True, True, False),
        )
        .val()
    )

    result = BaseStabilityAnalyzer().analyze(
        shape=centered
    )

    if not result.stable:
        raise RuntimeError(
            "Centered stability fixture should be stable."
        )

    if result.margin is None or result.margin < 19.0:
        raise RuntimeError(
            f"Unexpected stability margin: {result.margin}"
        )

    print(
        "stability fixture",
        f"margin={result.margin:.3f} mm",
        f"area={result.support_area:.3f} mm^2",
        f"points={result.support_point_count}",
        "OK",
    )


def main() -> None:
    _validate_thickness_regression()
    _validate_stability_regression()

    source = build_structural_body_source(
        SPEC_PATH
    )

    report = StructuralBodyValidator().validate(
        source=source,
        manufacturing_profile=ManufacturingProfile(),
        product_profile=ProductManufacturingProfile(),
    )

    print(
        "DOBO Manufacturability - Phase 7.4\n"
        "Structural Body Suite\n"
        "-----------------------------------"
    )

    for check in report.checks:
        suffix = ""

        if check.measured_value is not None:
            suffix += (
                f" measured={check.measured_value:.3f}"
            )

        if check.required_value is not None:
            suffix += (
                f" required={check.required_value:.3f}"
            )

        if check.unit:
            suffix += f" {check.unit}"

        print(
            f"{check.label:<28} "
            f"{check.status.value:<14} "
            f"{check.code}"
            f"{suffix}"
        )

    print(
        "-----------------------------------"
    )

    blocking = report.blocking_errors

    print(
        "blocking errors",
        len(blocking),
    )

    if blocking:
        codes = [
            check.code
            for check in blocking
        ]

        raise RuntimeError(
            "Phase 7.4 structural validation has blocking errors: "
            f"{codes}"
        )

    print(
        "Phase 7.4 Structural Body Suite: Valid OK"
    )


if __name__ == "__main__":
    main()
