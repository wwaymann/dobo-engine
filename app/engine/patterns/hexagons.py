from typing import Literal, cast

import cadquery as cq

from base_surface import build_surface_grid
from context import EngineContext
from geometry_utils import create_surface_plane

PatternMode = Literal[
    "embossed",
    "engraved",
]


def build_hexagons(
    model: cq.Workplane,
    context: EngineContext,
) -> cq.Workplane:
    """
    Construye una malla de hexágonos sobre
    la superficie exterior del modelo.

    La distribución de filas y columnas se delega
    al Surface Engine mediante build_surface_grid().
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

    offset_first_row = bool(
        pattern_config.get(
            "offset_first_row",
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
        cell_size=cell_size,
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

    hexagon_shapes: list[cq.Shape] = []

    for position in positions:
        hexagon_shape = create_hexagon_shape(
            config=config,
            cell_size=cell_size,
            depth=depth,
            position_z=position.position_z,
            angle_degrees=position.angle_degrees,
            rotation=rotation,
            mode=mode,
        )

        hexagon_shapes.append(hexagon_shape)

    if not hexagon_shapes:
        context.add_operation("build_hexagons")
        return model

    model = apply_pattern_boolean(
        model=model,
        pattern_shapes=hexagon_shapes,
        mode=mode,
        pattern_name="hexagon",
    )

    context.add_operation("build_hexagons")

    return model


def validate_hexagon_config(
    cell_size: float,
    depth: float,
    mode: str,
) -> None:
    """
    Valida únicamente los parámetros propios
    de la geometría hexagonal.

    Los parámetros de distribución son validados
    por base_surface.py.
    """

    if cell_size <= 0:
        raise ValueError("Pattern cell_size must be greater than 0.")

    if depth <= 0:
        raise ValueError("Pattern depth must be greater than 0.")

    if mode not in {
        "embossed",
        "engraved",
    }:
        raise ValueError("Pattern mode must be " "'embossed' or 'engraved'.")


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
    Crea un hexágono individual orientado
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

    hexagon_workplane = (
        cq.Workplane(surface_plane)
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
