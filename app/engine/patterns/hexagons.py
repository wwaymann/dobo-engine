import math
from typing import Literal, cast

import cadquery as cq

from context import EngineContext
from geometry_utils import (
    arc_length_to_angle_degrees,
    create_surface_plane,
    get_radius_at_z,
)

PatternMode = Literal[
    "embossed",
    "engraved",
]


def build_hexagons(
    model: cq.Workplane,
    context: EngineContext,
) -> cq.Workplane:
    """
    Construye una malla de hexágonos sobre una
    superficie cilíndrica o cónica.

    Los hexágonos se generan primero y se aplica
    una sola operación booleana al final.
    """

    config = context.config
    pattern_config = config.get(
        "pattern",
        {},
    )

    if not pattern_config.get(
        "enabled",
        False,
    ):
        return model

    cell_size = float(
        pattern_config.get(
            "cell_size",
            6,
        )
    )

    depth = float(
        pattern_config.get(
            "depth",
            1,
        )
    )

    rotation = float(
        pattern_config.get(
            "rotation",
            30,
        )
    )

    spacing_x = float(
        pattern_config.get(
            "spacing_x",
            16,
        )
    )

    spacing_y = float(
        pattern_config.get(
            "spacing_y",
            14,
        )
    )

    start_z = float(
        pattern_config.get(
            "start_z",
            25,
        )
    )

    end_z = float(
        pattern_config.get(
            "end_z",
            75,
        )
    )

    angle_start = float(
        pattern_config.get(
            "angle_start",
            -40,
        )
    )

    angle_end = float(
        pattern_config.get(
            "angle_end",
            40,
        )
    )

    row_offset = bool(
        pattern_config.get(
            "row_offset",
            True,
        )
    )

    mode_value = str(
        pattern_config.get(
            "mode",
            "embossed",
        )
    ).lower()

    validate_hexagon_config(
        config=config,
        cell_size=cell_size,
        depth=depth,
        spacing_x=spacing_x,
        spacing_y=spacing_y,
        start_z=start_z,
        end_z=end_z,
        angle_start=angle_start,
        angle_end=angle_end,
        mode=mode_value,
    )

    mode = cast(
        PatternMode,
        mode_value,
    )

    hexagon_shapes: list[cq.Shape] = []

    current_z = start_z
    row_index = 0

    while current_z <= end_z + 1e-9:
        radius = get_radius_at_z(
            config=config,
            position_z=current_z,
        )

        if radius <= 0:
            raise ValueError("Pattern surface radius must be greater than 0.")

        angle_step = arc_length_to_angle_degrees(
            arc_length=spacing_x,
            radius=radius,
        )

        angles = build_angle_positions(
            angle_start=angle_start,
            angle_end=angle_end,
            angle_step=angle_step,
        )

        # Desplaza la primera fila, la tercera,
        # la quinta, etc., media separación.
        if row_offset and row_index % 2 == 0:
            shifted_angles: list[float] = []

            for angle in angles:
                shifted_angle = angle + angle_step / 2

                if shifted_angle <= angle_end:
                    shifted_angles.append(shifted_angle)

            angles = shifted_angles

        for angle_degrees in angles:
            hexagon_shape = create_hexagon_shape(
                config=config,
                cell_size=cell_size,
                depth=depth,
                position_z=current_z,
                angle_degrees=angle_degrees,
                rotation=rotation,
                mode=mode,
            )

            hexagon_shapes.append(hexagon_shape)

        current_z += spacing_y
        row_index += 1

    if not hexagon_shapes:
        context.add_operation("build_hexagons")
        return model

    base_shape = cast(
        cq.Shape,
        model.val(),
    )

    try:
        if mode == "embossed":
            result_shape = base_shape.fuse(*hexagon_shapes)

        else:
            result_shape = base_shape.cut(*hexagon_shapes)

    except Exception as error:
        raise RuntimeError(
            "Could not apply the hexagon pattern " "to the model."
        ) from error

    context.add_operation("build_hexagons")

    return cq.Workplane(obj=result_shape)


def validate_hexagon_config(
    config: dict,
    cell_size: float,
    depth: float,
    spacing_x: float,
    spacing_y: float,
    start_z: float,
    end_z: float,
    angle_start: float,
    angle_end: float,
    mode: str,
) -> None:
    """
    Valida la configuración del patrón hexagonal.
    """

    height = float(config["height"])

    if height <= 0:
        raise ValueError("Model height must be greater than 0.")

    if cell_size <= 0:
        raise ValueError("Pattern cell_size must be greater than 0.")

    if depth <= 0:
        raise ValueError("Pattern depth must be greater than 0.")

    if spacing_x <= 0:
        raise ValueError("Pattern spacing_x must be greater than 0.")

    if spacing_y <= 0:
        raise ValueError("Pattern spacing_y must be greater than 0.")

    if start_z < 0:
        raise ValueError("Pattern start_z cannot be negative.")

    if end_z > height:
        raise ValueError("Pattern end_z cannot exceed model height.")

    if start_z > end_z:
        raise ValueError("Pattern start_z cannot be greater than end_z.")

    if angle_start > angle_end:
        raise ValueError("Pattern angle_start cannot be greater " "than angle_end.")

    if angle_start < -180:
        raise ValueError("Pattern angle_start cannot be less than -180.")

    if angle_end > 180:
        raise ValueError("Pattern angle_end cannot be greater than 180.")

    if mode not in {
        "embossed",
        "engraved",
    }:
        raise ValueError("Pattern mode must be " "'embossed' or 'engraved'.")


def build_angle_positions(
    angle_start: float,
    angle_end: float,
    angle_step: float,
) -> list[float]:
    """
    Genera las posiciones angulares de una fila.
    """

    if angle_step <= 0:
        raise ValueError("Pattern angle step must be greater than 0.")

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


def create_hexagon_shape(
    config: dict,
    cell_size: float,
    depth: float,
    position_z: float,
    angle_degrees: float,
    rotation: float,
    mode: PatternMode,
) -> cq.Shape:
    """
    Crea un hexágono individual adaptado al plano
    tangente de la superficie.

    cell_size representa el diámetro exterior
    aproximado del hexágono.
    """

    overlap = max(
        1.0,
        depth,
    )

    if mode == "embossed":
        hexagon_plane = create_surface_plane(
            config=config,
            position_z=position_z,
            angle_degrees=angle_degrees,
            overlap=overlap,
            outward=False,
            rotation_degrees=rotation,
        )

        extrusion_distance = depth + overlap

    else:
        hexagon_plane = create_surface_plane(
            config=config,
            position_z=position_z,
            angle_degrees=angle_degrees,
            overlap=overlap,
            outward=True,
            rotation_degrees=rotation,
        )

        extrusion_distance = -(depth + overlap)

    hexagon_workplane = (
        cq.Workplane(hexagon_plane)
        .polygon(
            6,
            cell_size,
        )
        .extrude(extrusion_distance)
    )

    hexagon_shape = hexagon_workplane.val()

    if not isinstance(
        hexagon_shape,
        cq.Shape,
    ):
        raise RuntimeError("The hexagon geometry could not be created.")

    return hexagon_shape
