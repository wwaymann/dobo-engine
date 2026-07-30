from collections.abc import Callable

import cadquery as cq

from context import EngineContext

PipelineStage = Callable[
    [cq.Workplane | None, EngineContext],
    cq.Workplane,
]


def run_pipeline(
    stages: list[PipelineStage],
    context: EngineContext,
) -> cq.Workplane:
    """
    Ejecuta las etapas del motor en el orden indicado.
    """

    model: cq.Workplane | None = None

    for stage in stages:
        model = stage(model, context)

    if model is None:
        raise RuntimeError("The pipeline did not generate a model.")

    return model
