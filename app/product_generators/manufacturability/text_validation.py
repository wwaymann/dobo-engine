from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True, slots=True)
class TextStrokeResult:
    available: bool
    minimum_stroke: float | None
    printable: bool | None


@dataclass(frozen=True, slots=True)
class TextDepthResult:
    available: bool
    measured_depth: float | None
    valid: bool | None


@dataclass(frozen=True, slots=True)
class TextRegionVolumeResult:
    available: bool
    volume: float | None
    valid: bool | None


class TextStrokeAnalyzer:
    """
    Estimate the minimum printable text stroke from an explicit planar
    reference face or wire set.

    The analyzer intentionally does not infer typography from the final
    decorated product. The text generator must provide the planar source
    geometry used to create the surface decoration.

    For a planar text face, a practical local-stroke estimate is obtained
    from area/perimeter:

        width ~= 2 * area / perimeter

    For a long rectangular stroke this converges to its physical width.
    For complex glyphs it is a conservative manufacturability proxy and is
    stable across fonts without rasterization.
    """

    def analyze(
        self,
        *,
        planar_text: cq.Shape | None,
        minimum_required: float,
    ) -> TextStrokeResult:
        if planar_text is None:
            return TextStrokeResult(
                available=False,
                minimum_stroke=None,
                printable=None,
            )

        faces = tuple(
            planar_text.Faces()
        )

        if not faces:
            return TextStrokeResult(
                available=True,
                minimum_stroke=0.0,
                printable=False,
            )

        estimates: list[float] = []

        for face in faces:
            area = float(
                face.Area()
            )

            perimeter = sum(
                float(edge.Length())
                for edge in face.Edges()
            )

            if (
                area <= 0.0
                or perimeter <= 0.0
            ):
                continue

            width_estimate = (
                2.0
                * area
                / perimeter
            )

            if width_estimate > 0.0:
                estimates.append(
                    width_estimate
                )

        if not estimates:
            return TextStrokeResult(
                available=True,
                minimum_stroke=0.0,
                printable=False,
            )

        minimum = min(
            estimates
        )

        return TextStrokeResult(
            available=True,
            minimum_stroke=minimum,
            printable=(
                minimum
                >= minimum_required
            ),
        )


class TextDepthAnalyzer:
    """
    Validate explicit emboss/deboss depth.

    Depth is semantic input from the text operation, not reconstructed from
    the final B-Rep. This avoids confusing local curvature or material
    interfaces with decoration depth.
    """

    def analyze(
        self,
        *,
        depth: float | None,
        minimum_required: float,
    ) -> TextDepthResult:
        if depth is None:
            return TextDepthResult(
                available=False,
                measured_depth=None,
                valid=None,
            )

        measured = abs(
            float(depth)
        )

        return TextDepthResult(
            available=True,
            measured_depth=measured,
            valid=(
                measured
                >= minimum_required
            ),
        )


class TextRegionVolumeAnalyzer:
    """
    Validate the actual printable text material/removal region.
    """

    def analyze(
        self,
        *,
        text_region: cq.Shape | None,
        minimum_required: float,
    ) -> TextRegionVolumeResult:
        if text_region is None:
            return TextRegionVolumeResult(
                available=False,
                volume=None,
                valid=None,
            )

        try:
            valid_shape = bool(
                text_region.isValid()
            )
            solids = len(
                text_region.Solids()
            )
            volume = float(
                text_region.Volume()
            )
        except Exception:
            return TextRegionVolumeResult(
                available=True,
                volume=0.0,
                valid=False,
            )

        valid = bool(
            valid_shape
            and solids >= 1
            and volume
            >= minimum_required
        )

        return TextRegionVolumeResult(
            available=True,
            volume=volume,
            valid=valid,
        )
