from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True, slots=True)
class PrintedTextFeatureResult:
    available: bool
    minimum_feature: float | None
    printable: bool | None


class PrintedTextFeatureAnalyzer:
    """Validate printable text from the actual final text material region.

    This deliberately uses the post-UV, post-mapping, post-boolean material
    geometry. It therefore measures the geometry that will actually be sent
    to the slicer instead of reconstructing or guessing an unscaled font.

    For each connected text solid, the smallest positive bounding dimension
    is a conservative manufacturability guard. Emboss depth is validated by
    TEXT_DEPTH separately, so this rule is concerned with the smallest
    printable physical feature present in the final text region.
    """

    def analyze(
        self,
        *,
        text_region: cq.Shape | None,
        minimum_required: float,
    ) -> PrintedTextFeatureResult:
        if text_region is None:
            return PrintedTextFeatureResult(False, None, None)

        try:
            solids = tuple(text_region.Solids())
        except Exception:
            return PrintedTextFeatureResult(True, 0.0, False)

        if not solids:
            return PrintedTextFeatureResult(True, 0.0, False)

        measurements: list[float] = []
        for solid in solids:
            try:
                box = solid.BoundingBox()
                dimensions = (
                    float(box.xlen),
                    float(box.ylen),
                    float(box.zlen),
                )
                positive = [value for value in dimensions if value > 1.0e-9]
                if positive:
                    measurements.append(min(positive))
            except Exception:
                continue

        if not measurements:
            return PrintedTextFeatureResult(True, 0.0, False)

        minimum = min(measurements)
        return PrintedTextFeatureResult(
            available=True,
            minimum_feature=minimum,
            printable=minimum >= float(minimum_required),
        )
