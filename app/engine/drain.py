import cadquery as cq


def build_drain(pot: cq.Workplane, config: dict) -> cq.Workplane:
    """
    Agrega el drenaje al cuerpo de la maceta.

    Si drain_hole es False, devuelve la geometría
    sin modificaciones.
    """

    if not config.get("drain_hole", False):
        return pot

    drain_diameter = config["drain_diameter"]

    if drain_diameter <= 0:
        raise ValueError("Drain diameter must be greater than 0 mm")

    pot = pot.faces("<Z").workplane().hole(drain_diameter)

    return pot
