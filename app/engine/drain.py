import cadquery as cq

from context import EngineContext


def build_drain(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Agrega el drenaje al cuerpo de la maceta.

    Si drain_hole es False, devuelve la geometría
    sin modificaciones.
    """

    if model is None:
        raise ValueError(
            "build_drain requires an existing model."
        )

    config = context.config

    if not config.get("drain_hole", False):
        context.add_operation("build_drain")
        return model

    drain_diameter = config["drain_diameter"]

    if drain_diameter <= 0:
        raise ValueError(
            "Drain diameter must be greater than 0 mm."
        )

    model = (
        model
        .faces("<Z")
        .workplane()
        .hole(drain_diameter)
    )

    context.add_operation("build_drain")

    return model