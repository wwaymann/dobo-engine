import cadquery as cq

from context import EngineContext


def build_text(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Aplica texto al modelo.

    (Pendiente de implementación)
    """

    if model is None:
        raise ValueError(
            "build_text requires an existing model."
        )

    context.add_operation("build_text")

    return model