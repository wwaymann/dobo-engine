import cadquery as cq

from context import EngineContext


def build_decoration(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Agrega decoraciones.

    (Pendiente de implementación)
    """

    if model is None:
        raise ValueError(
            "build_decoration requires an existing model."
        )

    context.add_operation("build_decoration")

    return model