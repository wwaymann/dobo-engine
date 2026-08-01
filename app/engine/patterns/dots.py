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


def build_dots(
    model: cq.Workplane,
    context: EngineContext,
) -> cq.Workplane:
    """
    Construye una malla de puntos sobre una superficie
    cilíndrica o cónica.

    Los puntos se generan individualmente, pero la
    unión o el corte se realiza una sola vez al final.
    """

    config = context.config
    pattern_config = config.get("pattern", {})

    if not pattern_config.get("enabled", False):
        return model

    diameter = float(
        pattern_config.get(
            "diameter",
            3,
        )
    )

    depth = float(
        pattern_config.get(
            "depth",
            1,
        )
    )

    spacing_x = float(
        pattern_config.get(
            "spacing_x",
            15,
        )
    )

    spacing_y = float(
        pattern_config.get(
            "spacing_y",
            15,
        )
    )

    start_z = float(
        pattern_config.get(
            "start_z",
            20,
        )
    )

    end_z = float(
        pattern_config.get(
            "end_z",
            80,
        )
    )

    angle_start = float(
        pattern_config.get(
            "angle_start",
            -45,
        )
    )

    angle_end = float(
        pattern_config.get(
            "angle_end",
            45,
        )
    )

    mode_value = str(
        pattern_config.get(
            "mode",
            "embossed",
        )
    ).lower()

    validate_dots_config(
        config=config,
        diameter=diameter,
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

    dot_shapes: list[cq.Shape] = []

    current_z = start_z

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

        for angle_degrees in angles:
            dot_shape = create_dot_shape(
                config=config,
                diameter=diameter,
                depth=depth,
                position_z=current_z,
                angle_degrees=angle_degrees,
                mode=mode,
            )

            dot_shapes.append(dot_shape)

        current_z += spacing_y

    if not dot_shapes:
        context.add_operation("build_dots")
        return model

    base_shape = cast(
        cq.Shape,
        model.val(),
    )

    try:
        if mode == "embossed":
            result_shape = base_shape.fuse(*dot_shapes)

        else:
            result_shape = base_shape.cut(*dot_shapes)

    except Exception as error:
        raise RuntimeError(
            "Could not apply the dots pattern " "to the model."
        ) from error

    context.add_operation("build_dots")

    return cq.Workplane(obj=result_shape)


def validate_dots_config(
    config: dict,
    diameter: float,
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
    Valida la configuración del patrón de puntos.
    """

    height = float(config["height"])

    if height <= 0:
        raise ValueError("Model height must be greater than 0.")

    if diameter <= 0:
        raise ValueError("Pattern diameter must be greater than 0.")

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
    Genera las posiciones angulares para una fila.

    La separación se aproxima al valor solicitado
    en spacing_x y la distribución queda centrada.
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


def create_dot_shape(
    config: dict,
    diameter: float,
    depth: float,
    position_z: float,
    angle_degrees: float,
    mode: PatternMode,
) -> cq.Shape:
    """
    Crea un punto individual orientado sobre
    la superficie del modelo.

    Esta función no modifica la maceta.
    Solo devuelve la geometría del punto.
    """

    # Penetración suficiente para que la operación
    # booleana tenga una intersección real.
    overlap = max(
        1.0,
        depth,
    )

    if mode == "embossed":
        # El plano comienza dentro de la pared y
        # extruye hacia el exterior.
        dot_plane = create_surface_plane(
            config=config,
            position_z=position_z,
            angle_degrees=angle_degrees,
            overlap=overlap,
            outward=False,
            rotation_degrees=0,
        )

        extrusion_distance = depth + overlap

    else:
        # El plano comienza fuera de la pared y
        # extruye hacia el interior.
        dot_plane = create_surface_plane(
            config=config,
            position_z=position_z,
            angle_degrees=angle_degrees,
            overlap=overlap,
            outward=True,
            rotation_degrees=0,
        )

        extrusion_distance = -(depth + overlap)

    dot_workplane = (
        cq.Workplane(dot_plane).circle(diameter / 2).extrude(extrusion_distance)
    )

    dot_shape = dot_workplane.val()

    if not isinstance(
        dot_shape,
        cq.Shape,
    ):
        raise RuntimeError("The dot geometry could not be created.")

    return dot_shape
