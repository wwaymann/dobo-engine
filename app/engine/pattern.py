import cadquery as cq

from context import EngineContext


def build_pattern(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Aplica patrones decorativos.

    (Pendiente de implementación)
    """

    if model is None:
        raise ValueError(
            "build_pattern requires an existing model."
        )

    context.add_operation("build_pattern")

    return model