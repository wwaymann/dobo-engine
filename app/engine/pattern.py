import copy

import cadquery as cq

import patterns
from context import EngineContext
from patterns.registry import get_pattern_builder


def build_pattern(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Aplica uno o varios patrones registrados
    al modelo.
    """

    if model is None:
        raise ValueError("build_pattern requires an existing model.")

    config = context.config

    pattern_configs = get_pattern_configs(
        config=config,
    )

    if not pattern_configs:
        context.add_operation("build_pattern")
        return model

    for pattern_index, pattern_config in enumerate(pattern_configs):
        if not pattern_config.get(
            "enabled",
            False,
        ):
            continue

        pattern_type = str(
            pattern_config.get(
                "type",
                "none",
            )
        ).lower()

        if pattern_type == "none":
            continue

        component_config = copy.deepcopy(config)

        component_config["pattern"] = pattern_config

        component_context = EngineContext(component_config)

        try:
            builder = get_pattern_builder(pattern_type)

        except ValueError as error:
            raise ValueError(
                f"Unsupported pattern type at "
                f"patterns[{pattern_index}]: "
                f"{pattern_type}"
            ) from error

        model = builder(
            model,
            component_context,
        )

        for operation in component_context.operations:
            context.add_operation(operation)

    context.add_operation("build_pattern")

    return model


def get_pattern_configs(
    config: dict,
) -> list[dict]:
    """
    Obtiene la lista de configuraciones.

    Prioriza la estructura nueva "patterns".
    Mantiene compatibilidad con "pattern".
    """

    patterns_value = config.get("patterns")

    if patterns_value is not None:
        if not isinstance(
            patterns_value,
            list,
        ):
            raise ValueError("'patterns' must be a list.")

        pattern_configs: list[dict] = []

        for index, pattern_config in enumerate(patterns_value):
            if not isinstance(
                pattern_config,
                dict,
            ):
                raise ValueError(f"patterns[{index}] must be an object.")

            pattern_configs.append(pattern_config)

        return pattern_configs

    legacy_pattern = config.get("pattern")

    if legacy_pattern is None:
        return []

    if not isinstance(
        legacy_pattern,
        dict,
    ):
        raise ValueError("'pattern' must be an object.")

    return [
        legacy_pattern,
    ]
