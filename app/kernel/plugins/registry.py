"""
DOBO CAD Kernel

Generic Plugin Registry

Stores and discovers Kernel plugins without depending
on a specific plugin category.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Generic, TypeVar

PluginType = TypeVar("PluginType")


class PluginRegistry(
    Generic[PluginType],
):
    """
    Generic registry for Kernel plugins.

    A Registry stores plugin classes or instances
    under normalized string identifiers.
    """

    def __init__(self) -> None:
        self._plugins: dict[
            str,
            PluginType,
        ] = {}

        self._canonical_names: dict[
            str,
            str,
        ] = {}

    def register(
        self,
        name: str,
        plugin: PluginType,
        aliases: Iterable[str] = (),
    ) -> None:
        """
        Registers one plugin and its aliases.
        """

        canonical_name = self._normalize_name(name)

        normalized_aliases = tuple(self._normalize_name(alias) for alias in aliases)

        all_names = (
            canonical_name,
            *normalized_aliases,
        )

        if len(set(all_names)) != len(all_names):
            raise ValueError("Plugin name and aliases must be unique.")

        for plugin_name in all_names:
            if plugin_name in self._plugins:
                raise ValueError(f"Plugin '{plugin_name}' " "is already registered.")

        for plugin_name in all_names:
            self._plugins[plugin_name] = plugin

            self._canonical_names[plugin_name] = canonical_name

    def unregister(
        self,
        name: str,
    ) -> None:
        """
        Removes a plugin and every alias associated
        with its canonical name.
        """

        normalized_name = self._normalize_name(name)

        if normalized_name not in self._plugins:
            raise KeyError(f"Plugin '{name}' is not registered.")

        canonical_name = self._canonical_names[normalized_name]

        names_to_remove = [
            plugin_name
            for (
                plugin_name,
                stored_canonical_name,
            ) in self._canonical_names.items()
            if stored_canonical_name == canonical_name
        ]

        for plugin_name in names_to_remove:
            del self._plugins[plugin_name]

            del self._canonical_names[plugin_name]

    def get(
        self,
        name: str,
    ) -> PluginType:
        """
        Returns a registered plugin.
        """

        normalized_name = self._normalize_name(name)

        try:
            return self._plugins[normalized_name]

        except KeyError as error:
            raise KeyError(f"Unknown plugin: '{name}'.") from error

    def exists(
        self,
        name: str,
    ) -> bool:
        """
        Returns whether a plugin is registered.
        """

        normalized_name = self._normalize_name(name)

        return normalized_name in self._plugins

    def names(
        self,
        include_aliases: bool = False,
    ) -> tuple[str, ...]:
        """
        Returns registered plugin names.
        """

        if include_aliases:
            return tuple(sorted(self._plugins.keys()))

        canonical_names = set(self._canonical_names.values())

        return tuple(sorted(canonical_names))

    def clear(self) -> None:
        """
        Removes every registered plugin.
        """

        self._plugins.clear()
        self._canonical_names.clear()

    def __len__(self) -> int:
        """
        Returns the number of canonical plugins.
        """

        return len(self.names())

    def __contains__(
        self,
        name: object,
    ) -> bool:
        """
        Supports the expression:
        'circle' in registry
        """

        if not isinstance(
            name,
            str,
        ):
            return False

        return self.exists(name)

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:
        """
        Normalizes and validates a plugin name.
        """

        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError("Plugin name cannot be empty.")

        return normalized_name
