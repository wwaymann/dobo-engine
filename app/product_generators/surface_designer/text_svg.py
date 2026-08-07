from __future__ import annotations

import cadquery as cq


class TextSvgApproximation:
    """
    Phase 1 bridge for high-level text placement.

    CadQuery already generates real text solids. Until the dedicated
    text-outline extraction layer lands, this helper converts each
    character bounding box into a simple vector proxy for exercising
    the same surface-feature API end to end.

    This is deliberately marked as an approximation and is NOT claimed
    as final typography support.
    """

    def build_proxy_svg(
        self,
        text: str,
        *,
        size: float,
        spacing: float = 2.0,
    ) -> str:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text cannot be empty.")

        size = float(size)
        spacing = float(spacing)

        if size <= 0.0:
            raise ValueError("size must be positive.")

        x = 0.0
        rects: list[str] = []

        for char in text:
            if char.isspace():
                x += size * 0.45 + spacing
                continue

            width = size * 0.58
            height = size

            rects.append(
                f'<rect x="{x}" y="0" '
                f'width="{width}" height="{height}"/>'
            )

            x += width + spacing

        return (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            + "".join(rects)
            + "</svg>"
        )
