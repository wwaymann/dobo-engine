import math
from dataclasses import dataclass

from geometry_utils import (
    arc_length_to_angle_degrees,
    get_radius_at_z,
)


@dataclass(frozen=True)
class SurfacePosition:
    """
    Representa una posición lógica sobre
    la superficie del modelo.

    No contiene geometría.
    Solo indica:

    - altura;
    - ángulo;
    - fila;
    - columna.
    """

    position_z: float
    angle_degrees: float
    row_index: int
    column_index: int


def build_surface_grid(
    config: dict,
    spacing_x: float,
    spacing_y: float,
    start_z: float,
    end_z: float,
    angle_start: float,
    angle_end: float,
    row_offset: bool = False,
    offset_first_row: bool = False,
) -> list[SurfacePosition]:
    """
    Genera una malla de posiciones sobre una
    superficie cilíndrica o cónica.

    spacing_x se interpreta como una distancia
    aproximada sobre la superficie.

    spacing_y se interpreta en milímetros
    sobre el eje vertical.

    No crea geometría ni ejecuta booleanos.
    """

    validate_surface_grid(
        config=config,
        spacing_x=spacing_x,
        spacing_y=spacing_y,
        start_z=start_z,
        end_z=end_z,
        angle_start=angle_start,
        angle_end=angle_end,
    )

    positions: list[SurfacePosition] = []

    current_z = start_z
    row_index = 0

    while current_z <= end_z + 1e-9:
        radius = get_radius_at_z(
            config=config,
            position_z=current_z,
        )

        if radius <= 0:
            raise ValueError("Surface radius must be greater than 0.")

        angle_step = arc_length_to_angle_degrees(
            arc_length=spacing_x,
            radius=radius,
        )

        angles = build_angle_positions(
            angle_start=angle_start,
            angle_end=angle_end,
            angle_step=angle_step,
        )

        should_offset = row_offset and (
            (offset_first_row and row_index % 2 == 0)
            or (not offset_first_row and row_index % 2 == 1)
        )

        if should_offset:
            angles = offset_angle_positions(
                angles=angles,
                angle_step=angle_step,
                angle_end=angle_end,
            )

        for column_index, angle_degrees in enumerate(angles):
            positions.append(
                SurfacePosition(
                    position_z=current_z,
                    angle_degrees=angle_degrees,
                    row_index=row_index,
                    column_index=column_index,
                )
            )

        current_z += spacing_y
        row_index += 1

    return positions


def build_angle_positions(
    angle_start: float,
    angle_end: float,
    angle_step: float,
) -> list[float]:
    """
    Genera las posiciones angulares de una fila.

    La distribución utiliza un paso aproximado,
    manteniendo los elementos dentro del intervalo.
    """

    if angle_step <= 0:
        raise ValueError("Angle step must be greater than 0.")

    angular_range = angle_end - angle_start

    if angular_range <= 1e-9:
        return [
            angle_start,
        ]

    interval_count = max(
        1,
        int(round(angular_range / angle_step)),
    )

    actual_step = angular_range / interval_count

    return [angle_start + index * actual_step for index in range(interval_count + 1)]


def offset_angle_positions(
    angles: list[float],
    angle_step: float,
    angle_end: float,
) -> list[float]:
    """
    Desplaza una fila media separación angular.

    Se usa para distribuciones tipo ladrillo
    o panal de abeja.
    """

    offset = angle_step / 2

    shifted_angles = [
        angle + offset for angle in angles if angle + offset <= angle_end + 1e-9
    ]

    return shifted_angles


def validate_surface_grid(
    config: dict,
    spacing_x: float,
    spacing_y: float,
    start_z: float,
    end_z: float,
    angle_start: float,
    angle_end: float,
) -> None:
    """
    Valida los parámetros de la malla.
    """

    height = float(config["height"])

    if height <= 0:
        raise ValueError("Model height must be greater than 0.")

    if spacing_x <= 0:
        raise ValueError("Surface spacing_x must be greater than 0.")

    if spacing_y <= 0:
        raise ValueError("Surface spacing_y must be greater than 0.")

    if start_z < 0:
        raise ValueError("Surface start_z cannot be negative.")

    if end_z > height:
        raise ValueError("Surface end_z cannot exceed model height.")

    if start_z > end_z:
        raise ValueError("Surface start_z cannot be greater than end_z.")

    if angle_start > angle_end:
        raise ValueError("Surface angle_start cannot be greater " "than angle_end.")

    if angle_start < -180:
        raise ValueError("Surface angle_start cannot be less than -180.")

    if angle_end > 180:
        raise ValueError("Surface angle_end cannot be greater than 180.")

    if not math.isfinite(angle_start) or not math.isfinite(angle_end):
        raise ValueError("Surface angles must be finite numbers.")
