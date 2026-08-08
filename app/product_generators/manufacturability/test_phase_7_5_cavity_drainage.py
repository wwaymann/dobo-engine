from __future__ import annotations

from pathlib import Path
import math

import cadquery as cq

from .cavity import (
    ClosedCavityAnalyzer,
    DrainageAnalyzer,
    InternalVolumeAnalyzer,
)
from .local_thickness import LocalThicknessAnalyzer
from .product_profile import ProductManufacturingProfile
from .profile import ManufacturingProfile
from .source import (
    build_structural_body_source,
    make_planter_semantic_fixture,
)
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
        or not (
            0.35
            <= thin.minimum
            <= 0.45
        )
    ):
        raise RuntimeError(
            f"Thin fixture regression failed: {thin.minimum}"
        )

    if (
        thick.minimum is None
        or not (
            1.90
            <= thick.minimum
            <= 2.10
        )
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

    if (
        result.margin is None
        or result.margin < 19.0
    ):
        raise RuntimeError(
            f"Unexpected stability margin: {result.margin}"
        )

    print(
        "stability fixture",
        f"margin={result.margin:.3f} mm",
        f"area={result.support_area:.3f} mm^2",
        "OK",
    )


def _validate_planter_semantics() -> None:
    fixture = make_planter_semantic_fixture(
        outer_radius=30.0,
        height=50.0,
        wall=2.0,
        bottom=2.0,
        drainage_radius=2.0,
    )

    volume = InternalVolumeAnalyzer().analyze(
        fixture.internal_cavity
    )

    expected_volume = (
        math.pi
        * 28.0
        * 28.0
        * 48.0
    )

    if (
        not volume.available
        or not volume.valid
        or volume.volume is None
    ):
        raise RuntimeError(
            "Planter cavity fixture was not validated."
        )

    relative_error = abs(
        volume.volume
        - expected_volume
    ) / expected_volume

    if relative_error > 1.0e-4:
        raise RuntimeError(
            "Planter cavity volume mismatch: "
            f"{volume.volume} vs {expected_volume}"
        )

    drainage = DrainageAnalyzer().analyze(
        structural_body=(
            fixture.structural_body
        ),
        internal_cavity=(
            fixture.internal_cavity
        ),
        drainage_tools=(
            fixture.drainage_tools
        ),
    )

    if (
        not drainage.available
        or drainage.path_count != 1
        or not drainage.all_connected
    ):
        raise RuntimeError(
            "Planter drainage fixture did not validate: "
            f"{drainage}"
        )

    cavities = ClosedCavityAnalyzer().analyze(
        internal_cavity=(
            fixture.internal_cavity
        ),
        declared_closed_cavities=(
            fixture.declared_closed_cavities
        ),
    )

    if (
        not cavities.available
        or cavities.undeclared_count != 0
    ):
        raise RuntimeError(
            "Closed-cavity semantic fixture failed."
        )

    print(
        "planter semantic fixture",
        f"volume={volume.volume:.3f} mm^3",
        f"drains={drainage.path_count}",
        f"undeclared_cavities={cavities.undeclared_count}",
        "OK",
    )


def main() -> None:
    _validate_thickness_regression()
    _validate_stability_regression()
    _validate_planter_semantics()

    source = build_structural_body_source(
        SPEC_PATH
    )

    report = StructuralBodyValidator().validate(
        source=source,
        manufacturing_profile=ManufacturingProfile(),
        product_profile=ProductManufacturingProfile(),
    )

    print(
        "DOBO Manufacturability - Phase 7.5\n"
        "Cavity & Drainage Semantics\n"
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
        raise RuntimeError(
            "Phase 7.5 structural validation has blocking errors: "
            f"{[check.code for check in blocking]}"
        )

    print(
        "NOTE: current Phase-4 hybrid product does not expose "
        "cavity/drainage semantics, so those checks remain NOT_AVAILABLE "
        "for that specific stress-test product."
    )

    print(
        "Phase 7.5 Cavity & Drainage Semantics: Valid OK"
    )


if __name__ == "__main__":
    main()
