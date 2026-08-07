from __future__ import annotations


class SurfaceDesignerSvgFactory:
    @staticmethod
    def badge(
        *,
        width: float,
        height: float,
        kind: str = "rectangle",
    ) -> str:
        width = float(width)
        height = float(height)

        if width <= 0.0 or height <= 0.0:
            raise ValueError(
                "Badge dimensions must be positive."
            )

        if kind == "rectangle":
            return (
                '<svg xmlns="http://www.w3.org/2000/svg">'
                f'<rect x="0" y="0" width="{width}" height="{height}"/>'
                "</svg>"
            )

        if kind == "round":
            rx = width / 2.0
            ry = height / 2.0

            return (
                '<svg xmlns="http://www.w3.org/2000/svg">'
                f'<ellipse cx="{rx}" cy="{ry}" rx="{rx}" ry="{ry}"/>'
                "</svg>"
            )

        if kind == "diamond":
            cx = width / 2.0
            cy = height / 2.0

            points = (
                f"{cx},0 "
                f"{width},{cy} "
                f"{cx},{height} "
                f"0,{cy}"
            )

            return (
                '<svg xmlns="http://www.w3.org/2000/svg">'
                f'<polygon points="{points}"/>'
                "</svg>"
            )

        raise ValueError(
            f"Unsupported badge kind '{kind}'."
        )

    @staticmethod
    def frame(
        *,
        width: float,
        height: float,
        border: float,
    ) -> str:
        width = float(width)
        height = float(height)
        border = float(border)

        if (
            width <= 0.0
            or height <= 0.0
            or border <= 0.0
        ):
            raise ValueError(
                "Frame dimensions must be positive."
            )

        if (
            border * 2.0 >= width
            or border * 2.0 >= height
        ):
            raise ValueError(
                "Frame border is too large."
            )

        inner_x = border
        inner_y = border
        inner_w = width - 2.0 * border
        inner_h = height - 2.0 * border

        return (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="0" y="0" width="{width}" height="{height}"/>'
            f'<rect x="{inner_x}" y="{inner_y}" '
            f'width="{inner_w}" height="{inner_h}"/>'
            "</svg>"
        )
