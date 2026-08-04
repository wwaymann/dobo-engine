import copy

import cadquery as cq

import decorations
from context import EngineContext
from decorations.registry import (
    get_decoration_builder,
)


def build_decoration(
    model: cq.Workplane | None,
    context: EngineContext,
) -> cq.Workplane:
    """
    Aplica una o varias decoraciones
    sobre el modelo.

    Cada decoración es independiente
    y es construida mediante el
    Decoration Registry.
    """

    if model is None:
        raise ValueError("build_decoration requires an existing model.")

    config = context.config

    decoration_configs = get_decoration_configs(
        config=config,
    )

    if not decoration_configs:
        context.add_operation("build_decoration")

        return model

    for decoration_index, decoration_config in enumerate(decoration_configs):
        if not decoration_config.get(
            "enabled",
            False,
        ):
            continue

        decoration_type = str(
            decoration_config.get(
                "type",
                "none",
            )
        ).lower()

        if decoration_type == "none":
            continue

        component_config = copy.deepcopy(config)

        component_config["decoration"] = decoration_config

        component_context = EngineContext(component_config)

        try:
            builder = get_decoration_builder(decoration_type)

        except ValueError as error:
            raise ValueError(
                "Unsupported decoration "
                f"type at decorations[{decoration_index}]: "
                f"{decoration_type}"
            ) from error

        model = builder(
            model,
            component_context,
        )

        for operation in component_context.operations:
            context.add_operation(operation)

    context.add_operation("build_decoration")

    return model


def get_decoration_configs(
    config: dict,
) -> list[dict]:
    """
    Devuelve la lista de decoraciones.

    Mantiene compatibilidad futura con
    una decoración única.
    """

    decorations_value = config.get("decorations")

    if decorations_value is None:
        return []

    if not isinstance(
        decorations_value,
        list,
    ):
        raise ValueError("'decorations' must be a list.")

    decoration_configs: list[dict] = []

    for index, decoration_config in enumerate(decorations_value):
        if not isinstance(
            decoration_config,
            dict,
        ):
            raise ValueError(f"decorations[{index}] " "must be an object.")

        decoration_configs.append(decoration_config)

    return decoration_configs
