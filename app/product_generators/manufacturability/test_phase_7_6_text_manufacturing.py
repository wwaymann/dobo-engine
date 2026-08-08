from __future__ import annotations

import math

import cadquery as cq

from .profile import ManufacturingProfile
from .text_validation import (
    TextDepthAnalyzer,
    TextRegionVolumeAnalyzer,
    TextStrokeAnalyzer,
)


def _rect_face(
    width: float,
    height: float,
) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .rect(
            width,
            height,
        )
        .extrude(
            0.01
        )
        .faces(">Z")
        .val()
    )


def _solid_box(
    x: float,
    y: float,
    z: float,
) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .box(
            x,
            y,
            z,
        )
        .findSolid()
    )


def _validate_stroke() -> None:
    profile = ManufacturingProfile()
    analyzer = TextStrokeAnalyzer()

    # Long rectangle approximates a real glyph stroke well:
    # 2*A/P -> ~stroke width when length >> width.
    thin = analyzer.analyze(
        planar_text=_rect_face(
            20.0,
            0.30,
        ),
        minimum_required=(
            profile.min_text_stroke
        ),
    )

    thick = analyzer.analyze(
        planar_text=_rect_face(
            20.0,
            1.00,
        ),
        minimum_required=(
            profile.min_text_stroke
        ),
    )

    if (
        thin.minimum_stroke is None
        or thin.printable is not False
    ):
        raise RuntimeError(
            f"Thin text stroke fixture failed: {thin}"
        )

    if (
        thick.minimum_stroke is None
        or thick.printable is not True
    ):
        raise RuntimeError(
            f"Thick text stroke fixture failed: {thick}"
        )

    print(
        "text stroke fixtures",
        f"thin={thin.minimum_stroke:.3f}",
        f"thick={thick.minimum_stroke:.3f}",
        "OK",
    )


def _validate_depth() -> None:
    profile = ManufacturingProfile()
    analyzer = TextDepthAnalyzer()

    shallow = analyzer.analyze(
        depth=0.20,
        minimum_required=(
            profile.min_text_depth
        ),
    )

    emboss = analyzer.analyze(
        depth=1.80,
        minimum_required=(
            profile.min_text_depth
        ),
    )

    deboss = analyzer.analyze(
        depth=-1.40,
        minimum_required=(
            profile.min_text_depth
        ),
    )

    if shallow.valid is not False:
        raise RuntimeError(
            f"Shallow depth fixture failed: {shallow}"
        )

    if emboss.valid is not True:
        raise RuntimeError(
            f"Emboss depth fixture failed: {emboss}"
        )

    if deboss.valid is not True:
        raise RuntimeError(
            f"Deboss depth fixture failed: {deboss}"
        )

    print(
        "text depth fixtures",
        f"shallow={shallow.measured_depth:.3f}",
        f"emboss={emboss.measured_depth:.3f}",
        f"deboss={deboss.measured_depth:.3f}",
        "OK",
    )


def _validate_region_volume() -> None:
    profile = ManufacturingProfile()
    analyzer = TextRegionVolumeAnalyzer()

    small = analyzer.analyze(
        text_region=_solid_box(
            1.0,
            1.0,
            0.5,
        ),
        minimum_required=(
            profile.min_text_region_volume
        ),
    )

    valid = analyzer.analyze(
        text_region=_solid_box(
            10.0,
            5.0,
            1.0,
        ),
        minimum_required=(
            profile.min_text_region_volume
        ),
    )

    if small.valid is not False:
        raise RuntimeError(
            f"Small text region fixture failed: {small}"
        )

    if valid.valid is not True:
        raise RuntimeError(
            f"Valid text region fixture failed: {valid}"
        )

    print(
        "text volume fixtures",
        f"small={small.volume:.3f}",
        f"valid={valid.volume:.3f}",
        "OK",
    )


def _validate_current_product_semantics() -> None:
    """
    Validate the known Phase-5 text specification values.

    This deliberately tests semantic depth only. The current composition
    layer does not yet expose its planar text source as a manufacturing
    artifact, so printable-stroke remains source-dependent for that product.
    """
    profile = ManufacturingProfile()

    depth = TextDepthAnalyzer().analyze(
        depth=1.8,
        minimum_required=(
            profile.min_text_depth
        ),
    )

    if depth.valid is not True:
        raise RuntimeError(
            "Known Phase-5 text depth should pass."
        )

    print(
        "current product text depth",
        f"measured={depth.measured_depth:.3f}",
        f"required={profile.min_text_depth:.3f}",
        "OK",
    )


def main() -> None:
    _validate_stroke()
    _validate_depth()
    _validate_region_volume()
    _validate_current_product_semantics()

    print(
        "DOBO Manufacturability - Phase 7.6"
    )
    print(
        "Text Manufacturing Suite"
    )
    print(
        "-----------------------------------"
    )
    print(
        "TEXT_PRINTABLE_STROKE   ALGORITHM_VALIDATED_SOURCE_PENDING"
    )
    print(
        "TEXT_DEPTH              OK"
    )
    print(
        "TEXT_REGION_VOLUME      ALGORITHM_VALIDATED_SOURCE_PENDING"
    )
    print(
        "-----------------------------------"
    )
    print(
        "Phase 7.6 Text Manufacturing: Valid OK"
    )


if __name__ == "__main__":
    main()
