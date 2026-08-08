from __future__ import annotations

from dataclasses import dataclass
import math

import cadquery as cq


@dataclass(frozen=True, slots=True)
class ColorRegionSummary:
    name: str
    valid: bool
    volume: float
    solid_count: int


@dataclass(frozen=True, slots=True)
class ColorValidationResult:
    available: bool
    regions_valid: bool | None
    minimum_volume_ok: bool | None
    connectivity_ok: bool | None
    interface_integrity_ok: bool | None
    volume_error: float | None
    summaries: tuple[ColorRegionSummary, ...] = ()


class ColorRegionAnalyzer:
    """
    Validate an explicit material partition.

    Inputs:
      final_shape:
          Complete final printable solid.
      regions:
          Named color/material regions whose union should reproduce final_shape.

    Rules implemented:
      COLOR_REGIONS_VALID
      COLOR_REGION_MIN_VOLUME
      COLOR_REGION_CONNECTIVITY
      COLOR_INTERFACE_INTEGRITY

    Interface integrity is checked by volume conservation plus pairwise
    overlap rejection. The regions may touch at zero-volume interfaces.
    """

    def analyze(
        self,
        *,
        final_shape: cq.Shape | None,
        regions: dict[str, cq.Shape] | None,
        minimum_region_volume: float,
        volume_tolerance: float = 1.0e-3,
    ) -> ColorValidationResult:
        if final_shape is None or not regions:
            return ColorValidationResult(
                available=False,
                regions_valid=None,
                minimum_volume_ok=None,
                connectivity_ok=None,
                interface_integrity_ok=None,
                volume_error=None,
                summaries=(),
            )

        summaries: list[ColorRegionSummary] = []
        all_valid = True
        all_min_volume = True
        all_connected = True

        region_items = list(regions.items())

        for name, region in region_items:
            try:
                valid = bool(region.isValid())
                volume = float(region.Volume())
                solid_count = len(region.Solids())
            except Exception:
                valid = False
                volume = 0.0
                solid_count = 0

            summaries.append(
                ColorRegionSummary(
                    name=name,
                    valid=valid,
                    volume=volume,
                    solid_count=solid_count,
                )
            )

            all_valid = all_valid and valid and solid_count >= 1
            all_min_volume = (
                all_min_volume
                and volume >= minimum_region_volume
            )

            # A material region may contain several disconnected islands
            # (e.g. multiple studs). Connectivity therefore means every
            # connected component is a valid positive-volume solid, not that
            # the entire color must be one solid.
            if solid_count < 1:
                all_connected = False
            else:
                try:
                    component_ok = all(
                        solid.isValid()
                        and float(solid.Volume()) > 0.0
                        for solid in region.Solids()
                    )
                except Exception:
                    component_ok = False

                all_connected = (
                    all_connected
                    and component_ok
                )

        final_volume = float(final_shape.Volume())
        sum_region_volume = sum(
            item.volume for item in summaries
        )

        volume_error = abs(
            sum_region_volume - final_volume
        )

        no_pairwise_overlap = True

        for i in range(len(region_items)):
            for j in range(i + 1, len(region_items)):
                try:
                    overlap_volume = float(
                        region_items[i][1]
                        .intersect(region_items[j][1])
                        .Volume()
                    )
                except Exception:
                    no_pairwise_overlap = False
                    continue

                if overlap_volume > volume_tolerance:
                    no_pairwise_overlap = False

        interface_ok = bool(
            final_shape.isValid()
            and volume_error <= volume_tolerance
            and no_pairwise_overlap
        )

        return ColorValidationResult(
            available=True,
            regions_valid=all_valid,
            minimum_volume_ok=all_min_volume,
            connectivity_ok=all_connected,
            interface_integrity_ok=interface_ok,
            volume_error=volume_error,
            summaries=tuple(summaries),
        )
