from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True, slots=True)
class DecorationFeatureSizeResult:
    available: bool
    minimum_feature: float | None
    printable: bool | None


@dataclass(frozen=True, slots=True)
class DecorationRegionVolumeResult:
    available: bool
    volume: float | None
    valid: bool | None


class DecorationFeatureSizeAnalyzer:
    """
    Validate minimum printable feature size from explicit decoration geometry.

    The source must represent only the decoration before material partitioning.
    Each connected decorative solid is measured independently.
    """

    def analyze(
        self,
        *,
        decoration_geometry: cq.Shape | None,
        minimum_required: float,
    ) -> DecorationFeatureSizeResult:
        if decoration_geometry is None:
            return DecorationFeatureSizeResult(
                available=False,
                minimum_feature=None,
                printable=None,
            )

        try:
            solids = tuple(
                decoration_geometry.Solids()
            )
        except Exception:
            return DecorationFeatureSizeResult(
                available=True,
                minimum_feature=0.0,
                printable=False,
            )

        if not solids:
            return DecorationFeatureSizeResult(
                available=True,
                minimum_feature=0.0,
                printable=False,
            )

        measurements: list[float] = []

        for solid in solids:
            try:
                box = solid.BoundingBox()
                dimensions = (
                    float(box.xlen),
                    float(box.ylen),
                    float(box.zlen),
                )

                positive = [
                    value
                    for value in dimensions
                    if value > 1.0e-9
                ]

                if positive:
                    measurements.append(
                        min(positive)
                    )
            except Exception:
                continue

        if not measurements:
            return DecorationFeatureSizeResult(
                available=True,
                minimum_feature=0.0,
                printable=False,
            )

        minimum = min(
            measurements
        )

        return DecorationFeatureSizeResult(
            available=True,
            minimum_feature=minimum,
            printable=(
                minimum
                >= minimum_required
            ),
        )


class DecorationRegionVolumeAnalyzer:
    """
    Validate the explicit printable decoration material region.
    """

    def analyze(
        self,
        *,
        decoration_region: cq.Shape | None,
        minimum_required: float,
    ) -> DecorationRegionVolumeResult:
        if decoration_region is None:
            return DecorationRegionVolumeResult(
                available=False,
                volume=None,
                valid=None,
            )

        try:
            valid_shape = bool(
                decoration_region.isValid()
            )
            solids = len(
                decoration_region.Solids()
            )
            volume = float(
                decoration_region.Volume()
            )
        except Exception:
            return DecorationRegionVolumeResult(
                available=True,
                volume=0.0,
                valid=False,
            )

        return DecorationRegionVolumeResult(
            available=True,
            volume=volume,
            valid=bool(
                valid_shape
                and solids >= 1
                and volume >= minimum_required
            ),
        )
