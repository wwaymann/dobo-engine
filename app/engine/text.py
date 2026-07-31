import math
from typing import Literal, cast

import cadquery as cq

from context import EngineContext

TextAlignment = Literal[
    "left",
    "center",
    "right",
]

TextMode = Literal[
    "embossed",
    "engraved",
]

TextMapping = Literal[
    "auto",
    "curved",
    "planar",
]

FontKind = Literal[
    "regular",
    "bold",
    "italic",
]


def build_text(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Agrega una o varias líneas de texto al modelo.

    Capacidades:

    - Texto curvo sobre cilindros y conos.
    - Texto plano sobre superficies planas.
    - Relieve o grabado.
    - Posición angular alrededor del objeto.
    - Rotación diagonal.
    - Selección de fuente.
    - Varias líneas.
    - Alineación horizontal.
    """

    if model is None:
        raise ValueError("build_text requires an existing model.")

    config = context.config
    text_config = config.get("text", {})

    content = str(
        text_config.get(
            "content",
            "",
        )
    ).strip()

    if not content:
        context.add_operation("build_text")
        return model

    font_size = float(
        text_config.get(
            "font_size",
            10,
        )
    )

    depth = float(
        text_config.get(
            "depth",
            1,
        )
    )

    position_z = float(
        text_config.get(
            "position_z",
            float(config["height"]) / 2,
        )
    )

    letter_spacing = float(
        text_config.get(
            "letter_spacing",
            1.5,
        )
    )

    line_spacing = float(
        text_config.get(
            "line_spacing",
            font_size * 0.35,
        )
    )

    angle_degrees = float(
        text_config.get(
            "angle",
            0,
        )
    )

    rotation_degrees = float(
        text_config.get(
            "rotation",
            0,
        )
    )

    mode_value = str(
        text_config.get(
            "mode",
            "embossed",
        )
    ).lower()

    mapping_value = str(
        text_config.get(
            "mapping",
            "auto",
        )
    ).lower()

    alignment_value = str(
        text_config.get(
            "alignment",
            "center",
        )
    ).lower()

    font_name = str(
        text_config.get(
            "font",
            "Arial",
        )
    ).strip()

    font_kind_value = str(
        text_config.get(
            "font_style",
            "regular",
        )
    ).lower()

    font_path_value = text_config.get("font_path")

    font_path = str(font_path_value).strip() if font_path_value else None

    shape = str(
        config.get(
            "shape",
            "round",
        )
    ).lower()

    validate_text_config(
        config=config,
        font_size=font_size,
        depth=depth,
        position_z=position_z,
        letter_spacing=letter_spacing,
        line_spacing=line_spacing,
        mode=mode_value,
        mapping=mapping_value,
        alignment=alignment_value,
        font_name=font_name,
        font_kind=font_kind_value,
    )

    mode = cast(
        TextMode,
        mode_value,
    )

    mapping = cast(
        TextMapping,
        mapping_value,
    )

    alignment = cast(
        TextAlignment,
        alignment_value,
    )

    font_kind = cast(
        FontKind,
        font_kind_value,
    )

    if mapping == "auto":
        if shape in {
            "round",
            "cylindrical",
            "conical",
        }:
            mapping = "curved"
        else:
            mapping = "planar"

    lines = content.splitlines()

    if not lines:
        lines = [content]

    line_step = font_size + line_spacing

    block_height = len(lines) * font_size + max(len(lines) - 1, 0) * line_spacing

    first_line_z = position_z + block_height / 2 - font_size / 2

    for line_index, line_content in enumerate(lines):
        line_z = first_line_z - line_index * line_step

        if not line_content:
            continue

        if mapping == "curved":
            model = build_curved_text_line(
                model=model,
                config=config,
                content=line_content,
                font_size=font_size,
                depth=depth,
                position_z=line_z,
                mode=mode,
                letter_spacing=letter_spacing,
                alignment=alignment,
                angle_degrees=angle_degrees,
                rotation_degrees=rotation_degrees,
                font_name=font_name,
                font_kind=font_kind,
                font_path=font_path,
            )

        elif mapping == "planar":
            model = build_planar_text_line(
                model=model,
                config=config,
                content=line_content,
                font_size=font_size,
                depth=depth,
                position_z=line_z,
                mode=mode,
                alignment=alignment,
                angle_degrees=angle_degrees,
                rotation_degrees=rotation_degrees,
                font_name=font_name,
                font_kind=font_kind,
                font_path=font_path,
            )

    context.add_operation("build_text")

    return model


def validate_text_config(
    config: dict,
    font_size: float,
    depth: float,
    position_z: float,
    letter_spacing: float,
    line_spacing: float,
    mode: str,
    mapping: str,
    alignment: str,
    font_name: str,
    font_kind: str,
) -> None:
    """
    Valida los parámetros generales del texto.
    """

    height = float(config["height"])

    if height <= 0:
        raise ValueError("Model height must be greater than 0.")

    if font_size <= 0:
        raise ValueError("Text font_size must be greater than 0.")

    if depth <= 0:
        raise ValueError("Text depth must be greater than 0.")

    if position_z < 0 or position_z > height:
        raise ValueError("Text position_z must be inside " "the model height.")

    if letter_spacing < 0:
        raise ValueError("Text letter_spacing cannot be negative.")

    if line_spacing < 0:
        raise ValueError("Text line_spacing cannot be negative.")

    if mode not in {
        "embossed",
        "engraved",
    }:
        raise ValueError("Text mode must be " "'embossed' or 'engraved'.")

    if mapping not in {
        "auto",
        "curved",
        "planar",
    }:
        raise ValueError("Text mapping must be " "'auto', 'curved' or 'planar'.")

    if alignment not in {
        "left",
        "center",
        "right",
    }:
        raise ValueError("Text alignment must be " "'left', 'center' or 'right'.")

    if font_kind not in {
        "regular",
        "bold",
        "italic",
    }:
        raise ValueError("Text font_style must be " "'regular', 'bold' or 'italic'.")

    if not font_name:
        raise ValueError("Text font cannot be empty.")


def get_radius_at_z(
    config: dict,
    position_z: float,
) -> float:
    """
    Calcula el radio exterior del cuerpo
    en una posición vertical determinada.
    """

    height = float(config["height"])

    bottom_radius = float(config["bottom_diameter"]) / 2

    top_radius = float(config["top_diameter"]) / 2

    return bottom_radius + (top_radius - bottom_radius) * (position_z / height)


def get_radius_slope(
    config: dict,
) -> float:
    """
    Calcula la variación del radio respecto
    de la altura.

    Cilindro:
        pendiente = 0

    Cono abierto hacia arriba:
        pendiente > 0
    """

    height = float(config["height"])

    bottom_radius = float(config["bottom_diameter"]) / 2

    top_radius = float(config["top_diameter"]) / 2

    return (top_radius - bottom_radius) / height


def get_conical_surface_orientation(
    config: dict,
    radial_x: float,
    radial_y: float,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
]:
    """
    Devuelve la normal exterior y la dirección
    vertical local de una superficie cilíndrica
    o cónica.
    """

    radius_slope = get_radius_slope(
        config=config,
    )

    normalization = math.sqrt(1.0 + radius_slope**2)

    surface_normal = (
        radial_x / normalization,
        radial_y / normalization,
        -radius_slope / normalization,
    )

    surface_vertical = (
        radial_x * radius_slope / normalization,
        radial_y * radius_slope / normalization,
        1.0 / normalization,
    )

    return (
        surface_normal,
        surface_vertical,
    )


def rotate_local_axis(
    tangent: tuple[
        float,
        float,
        float,
    ],
    vertical: tuple[
        float,
        float,
        float,
    ],
    rotation_degrees: float,
) -> tuple[
    float,
    float,
    float,
]:
    """
    Rota el eje horizontal local dentro del plano
    tangente de la superficie.

    Este parámetro permite colocar el texto
    horizontal o diagonal.
    """

    rotation_radians = math.radians(rotation_degrees)

    cosine = math.cos(rotation_radians)

    sine = math.sin(rotation_radians)

    rotated_axis = (
        tangent[0] * cosine + vertical[0] * sine,
        tangent[1] * cosine + vertical[1] * sine,
        tangent[2] * cosine + vertical[2] * sine,
    )

    axis_length = math.sqrt(
        rotated_axis[0] ** 2 + rotated_axis[1] ** 2 + rotated_axis[2] ** 2
    )

    if axis_length <= 0:
        raise ValueError("Invalid text rotation axis.")

    return (
        rotated_axis[0] / axis_length,
        rotated_axis[1] / axis_length,
        rotated_axis[2] / axis_length,
    )


def create_text_geometry(
    workplane: cq.Workplane,
    content: str,
    font_size: float,
    distance: float,
    font_name: str,
    font_kind: FontKind,
    font_path: str | None,
    halign: TextAlignment,
) -> cq.Workplane:
    """
    Crea la geometría de texto aplicando
    nombre de fuente, estilo y archivo opcional.
    """

    if font_path:
        return workplane.text(
            content,
            font_size,
            distance,
            combine=False,
            font=font_name,
            fontPath=font_path,
            kind=font_kind,
            halign=halign,
            valign="center",
        )

    return workplane.text(
        content,
        font_size,
        distance,
        combine=False,
        font=font_name,
        kind=font_kind,
        halign=halign,
        valign="center",
    )


def measure_glyph_width(
    character: str,
    font_size: float,
    font_name: str,
    font_kind: FontKind,
    font_path: str | None,
) -> float:
    """
    Calcula el ancho geométrico de un carácter
    usando su caja envolvente.
    """

    if character.isspace():
        return font_size * 0.35

    fallback_width = font_size * 0.65

    try:
        glyph = create_text_geometry(
            workplane=cq.Workplane("XY"),
            content=character,
            font_size=font_size,
            distance=1.0,
            font_name=font_name,
            font_kind=font_kind,
            font_path=font_path,
            halign="center",
        )

        glyph_shape = cast(
            cq.Shape,
            glyph.combine().val(),
        )

        bounding_box = glyph_shape.BoundingBox()

        width = float(bounding_box.xlen)

    except (
        AttributeError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return fallback_width

    if not math.isfinite(width) or width <= 0:
        return fallback_width

    return width


def measure_text_widths(
    content: str,
    font_size: float,
    font_name: str,
    font_kind: FontKind,
    font_path: str | None,
) -> list[float]:
    """
    Mide el ancho individual de los caracteres.
    """

    return [
        measure_glyph_width(
            character=character,
            font_size=font_size,
            font_name=font_name,
            font_kind=font_kind,
            font_path=font_path,
        )
        for character in content
    ]


def get_initial_text_position(
    total_length: float,
    alignment: TextAlignment,
) -> float:
    """
    Calcula la posición inicial de una línea
    según su alineación.
    """

    if alignment == "left":
        return 0.0

    if alignment == "right":
        return -total_length

    return -total_length / 2


def build_curved_text_line(
    model: cq.Workplane,
    config: dict,
    content: str,
    font_size: float,
    depth: float,
    position_z: float,
    mode: TextMode,
    letter_spacing: float,
    alignment: TextAlignment,
    angle_degrees: float,
    rotation_degrees: float,
    font_name: str,
    font_kind: FontKind,
    font_path: str | None,
) -> cq.Workplane:
    """
    Construye una línea de texto adaptada
    horizontal y verticalmente a un cuerpo redondo.
    """

    radius = get_radius_at_z(
        config=config,
        position_z=position_z,
    )

    if radius <= 0:
        raise ValueError("Text radius must be greater than 0.")

    overlap = 0.5

    glyph_widths = measure_text_widths(
        content=content,
        font_size=font_size,
        font_name=font_name,
        font_kind=font_kind,
        font_path=font_path,
    )

    total_length = sum(glyph_widths) + max(len(content) - 1, 0) * letter_spacing

    current_length = get_initial_text_position(
        total_length=total_length,
        alignment=alignment,
    )

    base_angle = math.radians(angle_degrees)

    for index, character in enumerate(content):
        glyph_width = glyph_widths[index]

        glyph_center = current_length + glyph_width / 2

        if character.isspace():
            current_length += glyph_width + letter_spacing
            continue

        local_angle = -glyph_center / radius

        angle_radians = base_angle + local_angle

        radial_x = math.sin(angle_radians)

        radial_y = math.cos(angle_radians)

        x = radius * radial_x

        y = radius * radial_y

        tangent = (
            -math.cos(angle_radians),
            math.sin(angle_radians),
            0.0,
        )

        (
            plane_normal,
            surface_vertical,
        ) = get_conical_surface_orientation(
            config=config,
            radial_x=radial_x,
            radial_y=radial_y,
        )

        local_x_axis = rotate_local_axis(
            tangent=tangent,
            vertical=surface_vertical,
            rotation_degrees=rotation_degrees,
        )

        if mode == "embossed":
            plane_origin = (
                x - plane_normal[0] * overlap,
                y - plane_normal[1] * overlap,
                position_z - plane_normal[2] * overlap,
            )

        else:
            plane_origin = (
                x + plane_normal[0] * overlap,
                y + plane_normal[1] * overlap,
                position_z + plane_normal[2] * overlap,
            )

        text_plane = cq.Plane(
            origin=plane_origin,
            xDir=local_x_axis,
            normal=plane_normal,
        )

        glyph = create_text_geometry(
            workplane=cq.Workplane(text_plane),
            content=character,
            font_size=font_size,
            distance=depth + overlap,
            font_name=font_name,
            font_kind=font_kind,
            font_path=font_path,
            halign="center",
        )

        if mode == "embossed":
            model = model.union(glyph)
        else:
            model = model.cut(glyph)

        current_length += glyph_width + letter_spacing

    return model


def build_planar_text_line(
    model: cq.Workplane,
    config: dict,
    content: str,
    font_size: float,
    depth: float,
    position_z: float,
    mode: TextMode,
    alignment: TextAlignment,
    angle_degrees: float,
    rotation_degrees: float,
    font_name: str,
    font_kind: FontKind,
    font_path: str | None,
) -> cq.Workplane:
    """
    Construye una línea de texto sobre
    una superficie plana.

    angle controla qué lado del objeto se usa.

    rotation controla la inclinación del texto.
    """

    reference_radius = float(config["top_diameter"]) / 2

    overlap = 0.5

    angle_radians = math.radians(angle_degrees)

    radial_x = math.sin(angle_radians)

    radial_y = math.cos(angle_radians)

    tangent = (
        -math.cos(angle_radians),
        math.sin(angle_radians),
        0.0,
    )

    vertical = (
        0.0,
        0.0,
        1.0,
    )

    local_x_axis = rotate_local_axis(
        tangent=tangent,
        vertical=vertical,
        rotation_degrees=rotation_degrees,
    )

    plane_normal = (
        radial_x,
        radial_y,
        0.0,
    )

    surface_x = reference_radius * radial_x

    surface_y = reference_radius * radial_y

    if mode == "embossed":
        plane_origin = (
            surface_x - plane_normal[0] * overlap,
            surface_y - plane_normal[1] * overlap,
            position_z,
        )

    else:
        plane_origin = (
            surface_x + plane_normal[0] * overlap,
            surface_y + plane_normal[1] * overlap,
            position_z,
        )

    text_plane = cq.Plane(
        origin=plane_origin,
        xDir=local_x_axis,
        normal=plane_normal,
    )

    text_solid = create_text_geometry(
        workplane=cq.Workplane(text_plane),
        content=content,
        font_size=font_size,
        distance=depth + overlap,
        font_name=font_name,
        font_kind=font_kind,
        font_path=font_path,
        halign=alignment,
    )

    if mode == "embossed":
        return model.union(text_solid)

    return model.cut(text_solid)
