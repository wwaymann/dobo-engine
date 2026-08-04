import os
from dataclasses import dataclass

from svgpathtools import svg2paths2

Point2D = tuple[float, float]


@dataclass(frozen=True)
class SvgGeometry:
    """
    Geometría SVG convertida en contornos 2D.

    Los puntos quedan:
    - centrados en el origen;
    - escalados al ancho solicitado;
    - con el eje Y corregido para CAD.
    """

    contours: list[list[Point2D]]
    width: float
    height: float


def get_project_root() -> str:
    """
    Devuelve la carpeta raíz del proyecto.
    """

    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
        )
    )


def resolve_svg_path(
    file_path: str,
) -> str:
    """
    Convierte una ruta relativa del JSON
    en una ruta absoluta.
    """

    if os.path.isabs(file_path):
        resolved_path = file_path
    else:
        resolved_path = os.path.join(
            get_project_root(),
            file_path,
        )

    resolved_path = os.path.abspath(resolved_path)

    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"SVG file not found: {resolved_path}")

    return resolved_path


def load_svg_geometry(
    file_path: str,
    target_width: float,
    samples_per_path: int = 128,
) -> SvgGeometry:
    """
    Lee un SVG y lo convierte en contornos
    poligonales centrados y escalados.

    Esta versión admite contornos cerrados simples.
    """

    if target_width <= 0:
        raise ValueError("SVG target_width must be greater than 0.")

    if samples_per_path < 16:
        raise ValueError("SVG samples_per_path must be at least 16.")

    svg_path = resolve_svg_path(file_path)

    result = svg2paths2(svg_path)

    paths = result[0]

    raw_contours: list[list[Point2D]] = []

    for path in paths:
        if not path.isclosed():
            continue

        contour: list[Point2D] = []

        for sample_index in range(samples_per_path):
            parameter = sample_index / samples_per_path

            point = path.point(parameter)

            contour.append(
                (
                    float(point.real),
                    -float(point.imag),
                )
            )

        if len(contour) >= 3:
            raw_contours.append(contour)

    if not raw_contours:
        raise ValueError("The SVG does not contain usable closed paths.")

    all_x = [point[0] for contour in raw_contours for point in contour]

    all_y = [point[1] for contour in raw_contours for point in contour]

    minimum_x = min(all_x)
    maximum_x = max(all_x)
    minimum_y = min(all_y)
    maximum_y = max(all_y)

    source_width = maximum_x - minimum_x

    source_height = maximum_y - minimum_y

    if source_width <= 0:
        raise ValueError("SVG width must be greater than 0.")

    scale = target_width / source_width

    center_x = (minimum_x + maximum_x) / 2

    center_y = (minimum_y + maximum_y) / 2

    normalized_contours: list[list[Point2D]] = []

    for contour in raw_contours:
        normalized_contour = [
            (
                (point[0] - center_x) * scale,
                (point[1] - center_y) * scale,
            )
            for point in contour
        ]

        normalized_contours.append(normalized_contour)

    return SvgGeometry(
        contours=normalized_contours,
        width=target_width,
        height=source_height * scale,
    )
