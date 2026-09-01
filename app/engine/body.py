from .context import EngineContext
import cadquery as cq


def _solid_profile(radius_bottom: float, radius_top: float, height: float) -> cq.Workplane:
    """Keep true cylinders analytic; retain the historical loft for tapered bodies."""
    if abs(radius_bottom - radius_top) <= 1e-9:
        return cq.Workplane("XY").circle(radius_bottom).extrude(height)
    return (
        cq.Workplane("XY")
        .circle(radius_bottom)
        .workplane(offset=height)
        .circle(radius_top)
        .loft()
    )


def build_body(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """Construye el cuerpo hueco paramétrico de la maceta."""
    config = context.config

    top_diameter = config["top_diameter"]
    bottom_diameter = config["bottom_diameter"]
    height = config["height"]
    wall = config["wall_thickness"]
    bottom = config["bottom_thickness"]

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

    outer_body = _solid_profile(bottom_radius, top_radius, height)
    inner_body = _solid_profile(
        bottom_radius - wall,
        top_radius - wall,
        height,
    )

    body = outer_body.cut(inner_body.translate((0, 0, bottom)))
    context.add_operation("build_body")
    return body
