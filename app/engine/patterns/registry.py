from collections.abc import Callable

import cadquery as cq

from context import EngineContext

PatternBuilder = Callable[
    [cq.Workplane, EngineContext],
    cq.Workplane,
]


_PATTERN_REGISTRY: dict[
    str,
    PatternBuilder,
] = {}


def register_pattern(
    name: str,
    builder: PatternBuilder,
) -> None:
    """
    Registra un patrón.

    Lanza un error si el nombre ya existe.
    """

    key = name.lower()

    if key in _PATTERN_REGISTRY:
        raise ValueError(f"Pattern '{name}' is already registered.")

    _PATTERN_REGISTRY[key] = builder


def get_pattern_builder(
    name: str,
) -> PatternBuilder:
    """
    Devuelve el constructor asociado
    a un patrón.
    """

    key = name.lower()

    if key not in _PATTERN_REGISTRY:
        raise ValueError(f"Unknown pattern: '{name}'.")

    return _PATTERN_REGISTRY[key]


def is_registered(
    name: str,
) -> bool:
    """
    Indica si un patrón está registrado.
    """

    return name.lower() in _PATTERN_REGISTRY


def registered_patterns() -> list[str]:
    """
    Devuelve todos los patrones disponibles.
    """

    return sorted(_PATTERN_REGISTRY.keys())
