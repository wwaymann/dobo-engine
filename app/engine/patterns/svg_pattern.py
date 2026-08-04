from typing import Literal, cast

import cadquery as cq

from base_surface import build_surface_grid
from context import EngineContext
from geometry_utils import create_surface_plane
from svg_engine import (
    SvgGeometry,
    load_svg_geometry,
)

PatternMode = Literal[
    "embossed",
    "engraved",
]


def build_svg_pattern(
    model: cq.Workplane,
    context: EngineContext,
) -> cq.Workplane:
    """
    Coloca una geometría SVG una o varias veces
    sobre la superficie del modelo.
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

    file_path = str(
        pattern_config.get(
            "file",
            "",
        )
    ).strip()

    width = float(
        pattern_config.get(
            "width",
            20,
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
            30,
        )
    )

    spacing_y = float(
        pattern_config.get(
            "spacing_y",
            30,
        )
    )

    start_z = float(
        pattern_config.get(
            "start_z",
            40,
        )
    )

    end_z = float(
        pattern_config.get(
            "end_z",
            60,
        )
    )

    angle_start = float(
        pattern_config.get(
            "angle_start",
            -20,
        )
    )

    angle_end = float(
        pattern_config.get(
            "angle_end",
            20,
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

    samples_per_path = int(
        pattern_config.get(
            "samples_per_path",
            128,
        )
    )

    mode_value = str(
        pattern_config.get(
            "mode",
            "embossed",
        )
    ).lower()

    validate_svg_pattern(
        file_path=file_path,
        width=width,
        depth=depth,
        samples_per_path=samples_per_path,
        mode=mode_value,
    )

    mode = cast(
        PatternMode,
        mode_value,
    )

    svg_geometry = load_svg_geometry(
        file_path=file_path,
        target_width=width,
        samples_per_path=samples_per_path,
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

    svg_shapes: list[cq.Shape] = []

    for position in positions:
        instance_shapes = create_svg_instance_shapes(
            config=config,
            svg_geometry=svg_geometry,
            depth=depth,
            position_z=position.position_z,
            angle_degrees=(position.angle_degrees),
            rotation=rotation,
            mode=mode,
        )

        svg_shapes.extend(instance_shapes)

    if not svg_shapes:
        context.add_operation("build_svg_pattern")
        return model

    model = apply_svg_boolean(
        model=model,
        svg_shapes=svg_shapes,
        mode=mode,
    )

    context.add_operation("build_svg_pattern")

    return model


def validate_svg_pattern(
    file_path: str,
    width: float,
    depth: float,
    samples_per_path: int,
    mode: str,
) -> None:
    """
    Valida parámetros propios del patrón SVG.
    """

    if not file_path:
        raise ValueError("SVG pattern file cannot be empty.")

    if width <= 0:
        raise ValueError("SVG pattern width must be greater than 0.")

    if depth <= 0:
        raise ValueError("SVG pattern depth must be greater than 0.")

    if samples_per_path < 16:
        raise ValueError("SVG samples_per_path must be at least 16.")

    if mode not in {
        "embossed",
        "engraved",
    }:
        raise ValueError("SVG pattern mode must be " "'embossed' or 'engraved'.")


def create_svg_instance_shapes(
    config: dict,
    svg_geometry: SvgGeometry,
    depth: float,
    position_z: float,
    angle_degrees: float,
    rotation: float,
    mode: PatternMode,
) -> list[cq.Shape]:
    """
    Crea una instancia completa del SVG
    sobre un plano tangente.
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

    instance_shapes: list[cq.Shape] = []

    for contour in svg_geometry.contours:
        contour_workplane = (
            cq.Workplane(surface_plane)
            .polyline(contour)
            .close()
            .extrude(extrusion_distance)
        )

        contour_shape = contour_workplane.val()

        if not isinstance(
            contour_shape,
            cq.Shape,
        ):
            raise RuntimeError("SVG contour geometry could not be created.")

        instance_shapes.append(contour_shape)

    return instance_shapes


def apply_svg_boolean(
    model: cq.Workplane,
    svg_shapes: list[cq.Shape],
    mode: PatternMode,
) -> cq.Workplane:
    """
    Aplica todas las instancias SVG mediante
    una única operación booleana.
    """

    base_shape = model.val()

    if not isinstance(
        base_shape,
        cq.Shape,
    ):
        raise RuntimeError("The base model does not contain a valid shape.")

    try:
        if mode == "embossed":
            result_shape = base_shape.fuse(*svg_shapes)

        else:
            result_shape = base_shape.cut(*svg_shapes)

    except Exception as error:
        raise RuntimeError(
            "Could not apply the SVG pattern " "to the model."
        ) from error

    return cq.Workplane(obj=result_shape)


from patterns.registry import register_pattern

register_pattern(
    "svg",
    build_svg_pattern,
)

register_pattern(
    "logo",
    build_svg_pattern,
)
