import cadquery as cq

from context import EngineContext
from patterns.dots import build_dots


def build_pattern(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Coordina la construcción de patrones.
    """

    if model is None:
        raise ValueError("build_pattern requires an existing model.")

    config = context.config
    pattern_config = config.get("pattern", {})

    if not pattern_config.get("enabled", False):
        context.add_operation("build_pattern")
        return model

    pattern_type = str(
        pattern_config.get(
            "type",
            "none",
        )
    ).lower()

    if pattern_type == "dots":
        model = build_dots(
            model=model,
            context=context,
        )

    elif pattern_type != "none":
        raise ValueError(f"Unsupported pattern type: {pattern_type}")

    context.add_operation("build_pattern")

    return model
