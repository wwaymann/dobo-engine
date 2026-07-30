from context import EngineContext
import cadquery as cq


def build_body(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Construye el cuerpo hueco de la maceta.

    Este módulo inicia la geometría del pipeline,
    por lo que ignora el modelo recibido.
    """

    config = context.config

    top_diameter = config["top_diameter"]
    bottom_diameter = config["bottom_diameter"]
    height = config["height"]
    wall = config["wall_thickness"]
    bottom = config["bottom_thickness"]

    # ------------------------
    # Validations
    # ------------------------

    if top_diameter <= 0:
        raise ValueError("Top diameter must be greater than 0 mm")

    if bottom_diameter <= 0:
        raise ValueError("Bottom diameter must be greater than 0 mm")

    if height <= 0:
        raise ValueError("Height must be greater than 0 mm")

    if wall < 2:
        raise ValueError("Wall thickness must be >= 2 mm")

    if bottom < 3:
        raise ValueError("Bottom thickness must be >= 3 mm")

    top_radius = top_diameter / 2
    bottom_radius = bottom_diameter / 2

    if wall >= top_radius:
        raise ValueError("Wall thickness is too large for top diameter")

    if wall >= bottom_radius:
        raise ValueError("Wall thickness is too large for bottom diameter")

    if bottom >= height:
        raise ValueError("Bottom thickness must be smaller than pot height")

    # ------------------------
    # Outer body
    # ------------------------

    outer_body = (
        cq.Workplane("XY")
        .circle(bottom_radius)
        .workplane(offset=height)
        .circle(top_radius)
        .loft()
    )

    # ------------------------
    # Inner cavity
    # ------------------------

    inner_body = (
        cq.Workplane("XY")
        .circle(bottom_radius - wall)
        .workplane(offset=height)
        .circle(top_radius - wall)
        .loft()
    )

    # La cavidad se eleva para conservar
    # el espesor definido en la base.

    body = outer_body.cut(inner_body.translate((0, 0, bottom)))

    context.add_operation("build_body")

    return body
