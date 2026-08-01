from typing import Literal, cast

import cadquery as cq

from base_surface import build_surface_grid
from context import EngineContext
from geometry_utils import create_surface_plane

PatternMode = Literal[
    "embossed",
    "engraved",
]


def build_dots(
    model: cq.Workplane,
    context: EngineContext,
) -> cq.Workplane:
    """
    Construye una malla de puntos circulares
    sobre la superficie exterior del modelo.

    La distribución se delega completamente
    al Surface Engine.
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

    rotation = float(
        pattern_config.get(
            "rotation",
            0,
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

    row_offset = bool(
        pattern_config.get(
            "row_offset",
            False,
        )
    )

    offset_first_row = bool(
        pattern_config.get(
            "offset_first_row",
            False,
        )
    )

    mode_value = str(
        pattern_config.get(
            "mode",
            "embossed",
        )
    ).lower()

    validate_dots_config(
        diameter=diameter,
        depth=depth,
        mode=mode_value,
    )

    mode = cast(
        PatternMode,
        mode_value,
    )

    positions = build_surface_grid(
        config=config,
        spacing_x=spacing_x,
        spacing_y=spacing_y,
        start_z=start_z,
        end_z=end_z,
        angle_start=angle_start,
        angle_end=angle_end,
        row_offset=row_offset,
        offset_first_row=offset_first_row,
    )

    dot_shapes: list[cq.Shape] = []

    for position in positions:
        dot_shape = create_dot_shape(
            config=config,
            diameter=diameter,
            depth=depth,
            position_z=position.position_z,
            angle_degrees=position.angle_degrees,
            rotation=rotation,
            mode=mode,
        )

        dot_shapes.append(dot_shape)

    if not dot_shapes:
        context.add_operation("build_dots")
        return model

    model = apply_pattern_boolean(
        model=model,
        pattern_shapes=dot_shapes,
        mode=mode,
        pattern_name="dots",
    )

    context.add_operation("build_dots")

    return model


def validate_dots_config(
    diameter: float,
    depth: float,
    mode: str,
) -> None:
    """
    Valida únicamente los parámetros propios
    de la geometría circular.
    """

    if diameter <= 0:
        raise ValueError("Pattern diameter must be greater than 0.")

    if depth <= 0:
        raise ValueError("Pattern depth must be greater than 0.")

    if mode not in {
        "embossed",
        "engraved",
    }:
        raise ValueError("Pattern mode must be " "'embossed' or 'engraved'.")


def create_dot_shape(
    config: dict,
    diameter: float,
    depth: float,
    position_z: float,
    angle_degrees: float,
    rotation: float,
    mode: PatternMode,
) -> cq.Shape:
    """
    Crea un punto circular individual orientado
    sobre el plano tangente de la superficie.

    No modifica el modelo principal.
    """

    overlap = max(
        1.0,
        depth,
    )

    if mode == "embossed":
        surface_plane = create_surface_plane(
            config=config,
            position_z=position_z,
            angle_degrees=angle_degrees,
            overlap=overlap,
            outward=False,
            rotation_degrees=rotation,
        )

        extrusion_distance = depth + overlap

    else:
        surface_plane = create_surface_plane(
            config=config,
            position_z=position_z,
            angle_degrees=angle_degrees,
            overlap=overlap,
            outward=True,
            rotation_degrees=rotation,
        )

        extrusion_distance = -(depth + overlap)

    dot_workplane = (
        cq.Workplane(surface_plane).circle(diameter / 2).extrude(extrusion_distance)
    )

    dot_shape = dot_workplane.val()

    if not isinstance(
        dot_shape,
        cq.Shape,
    ):
        raise RuntimeError("The dot geometry could not be created.")

    return dot_shape


def apply_pattern_boolean(
    model: cq.Workplane,
    pattern_shapes: list[cq.Shape],
    mode: PatternMode,
    pattern_name: str,
) -> cq.Workplane:
    """
    Aplica todos los elementos del patrón mediante
    una sola operación booleana.
    """

    base_shape = model.val()

    if not isinstance(
        base_shape,
        cq.Shape,
    ):
        raise RuntimeError("The base model does not contain a valid shape.")

    try:
        if mode == "embossed":
            result_shape = base_shape.fuse(*pattern_shapes)

        else:
            result_shape = base_shape.cut(*pattern_shapes)

    except Exception as error:
        raise RuntimeError(
            f"Could not apply the {pattern_name} " "pattern to the model."
        ) from error

    return cq.Workplane(obj=result_shape)
