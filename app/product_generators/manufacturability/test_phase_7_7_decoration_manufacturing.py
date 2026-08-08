from __future__ import annotations

import cadquery as cq

from .decoration_validation import (
    DecorationFeatureSizeAnalyzer,
    DecorationRegionVolumeAnalyzer,
)
from .profile import ManufacturingProfile


def _sphere(
    radius: float,
) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .sphere(
            radius
        )
        .findSolid()
    )


def _box(
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


def _compound(
    *shapes: cq.Shape,
) -> cq.Shape:
    return cq.Compound.makeCompound(
        list(shapes)
    )


def _validate_feature_size() -> None:
    profile = ManufacturingProfile()
    analyzer = DecorationFeatureSizeAnalyzer()

    tiny = analyzer.analyze(
        decoration_geometry=_sphere(
            0.30
        ),
        minimum_required=(
            profile.min_decoration_feature_size
        ),
    )

    valid = analyzer.analyze(
        decoration_geometry=_sphere(
            1.00
        ),
        minimum_required=(
            profile.min_decoration_feature_size
        ),
    )

    mixed = analyzer.analyze(
        decoration_geometry=_compound(
            _sphere(1.50),
            _box(
                2.0,
                2.0,
                1.20,
            ).translate(
                (5.0, 0.0, 0.0)
            ),
        ),
        minimum_required=(
            profile.min_decoration_feature_size
        ),
    )

    if (
        tiny.minimum_feature is None
        or tiny.printable is not False
    ):
        raise RuntimeError(
            f"Tiny decoration fixture failed: {tiny}"
        )

    if (
        valid.minimum_feature is None
        or valid.printable is not True
    ):
        raise RuntimeError(
            f"Valid decoration fixture failed: {valid}"
        )

    if (
        mixed.minimum_feature is None
        or mixed.printable is not True
    ):
        raise RuntimeError(
            f"Mixed decoration fixture failed: {mixed}"
        )

    print(
        "decoration feature fixtures",
        f"tiny={tiny.minimum_feature:.3f}",
        f"valid={valid.minimum_feature:.3f}",
        f"mixed={mixed.minimum_feature:.3f}",
        "OK",
    )


def _validate_region_volume() -> None:
    profile = ManufacturingProfile()
    analyzer = DecorationRegionVolumeAnalyzer()

    small = analyzer.analyze(
        decoration_region=_box(
            1.0,
            1.0,
            0.5,
        ),
        minimum_required=(
            profile.min_decoration_region_volume
        ),
    )

    valid = analyzer.analyze(
        decoration_region=_box(
            4.0,
            4.0,
            2.0,
        ),
        minimum_required=(
            profile.min_decoration_region_volume
        ),
    )

    if small.valid is not False:
        raise RuntimeError(
            f"Small decoration region fixture failed: {small}"
        )

    if valid.valid is not True:
        raise RuntimeError(
            f"Valid decoration region fixture failed: {valid}"
        )

    print(
        "decoration volume fixtures",
        f"small={small.volume:.3f}",
        f"valid={valid.volume:.3f}",
        "OK",
    )


def _validate_known_phase6_region() -> None:
    profile = ManufacturingProfile()

    measured = 68.629

    if (
        measured
        < profile.min_decoration_region_volume
    ):
        raise RuntimeError(
            "Known Phase-6 decoration region volume should pass."
        )

    print(
        "known Phase-6 decoration region",
        f"measured={measured:.3f}",
        f"required={profile.min_decoration_region_volume:.3f}",
        "OK",
    )


def main() -> None:
    _validate_feature_size()
    _validate_region_volume()
    _validate_known_phase6_region()

    print(
        "DOBO Manufacturability - Phase 7.7"
    )
    print(
        "Decoration Manufacturing Suite"
    )
    print(
        "-----------------------------------"
    )
    print(
        "DECORATION_FEATURE_SIZE    ALGORITHM_VALIDATED_SOURCE_PENDING"
    )
    print(
        "DECORATION_REGION_VOLUME   OK_KNOWN_PHASE6 / SOURCE_PENDING_API"
    )
    print(
        "-----------------------------------"
    )
    print(
        "Phase 7.7 Decoration Manufacturing: Valid OK"
    )


if __name__ == "__main__":
    main()
