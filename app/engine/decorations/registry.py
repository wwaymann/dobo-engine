from collections.abc import Callable

import cadquery as cq

from context import EngineContext

DecorationBuilder = Callable[
    [cq.Workplane, EngineContext],
    cq.Workplane,
]


_DECORATION_REGISTRY: dict[
    str,
    DecorationBuilder,
] = {}


def register_decoration(
    name: str,
    builder: DecorationBuilder,
) -> None:
    """
    Registra un constructor de decoración.
    """

    key = name.lower()

    if key in _DECORATION_REGISTRY:
        raise ValueError(f"Decoration '{name}' is already registered.")

    _DECORATION_REGISTRY[key] = builder


def get_decoration_builder(
    name: str,
) -> DecorationBuilder:
    """
    Devuelve el constructor registrado.
    """

    key = name.lower()

    if key not in _DECORATION_REGISTRY:
        raise ValueError(f"Unknown decoration: '{name}'.")

    return _DECORATION_REGISTRY[key]


def registered_decorations() -> list[str]:
    """
    Lista todas las decoraciones disponibles.
    """

    return sorted(_DECORATION_REGISTRY.keys())
