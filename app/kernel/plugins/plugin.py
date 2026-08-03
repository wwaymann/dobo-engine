"""
DOBO CAD Kernel

Base Plugin Contract

Defines the common interface implemented by every
Kernel plugin.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Plugin(ABC):
    """
    Base class for every extensible Kernel component.

    Examples:

    - Provider
    - Pattern
    - Decoration
    - Exporter
    - Surface implementation
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique plugin identifier.

        The name is used by registries and configuration.
        """

    @property
    def aliases(self) -> tuple[str, ...]:
        """
        Optional alternative names for the plugin.
        """

        return ()

    @property
    def version(self) -> str:
        """
        Plugin version.

        Plugins may override this property.
        """

        return "1.0.0"

    @property
    def description(self) -> str:
        """
        Human-readable plugin description.
        """

        return ""

    def validate_plugin(self) -> None:
        """
        Validates common plugin information.
        """

        normalized_name = self.name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "Plugin name cannot be empty."
            )

        names = (
            normalized_name,
            *(
                alias.strip().lower()
                for alias in self.aliases
            ),
        )

        if any(
            not name
            for name in names
        ):
            raise ValueError(
                "Plugin aliases cannot be empty."
            )

        if len(set(names)) != len(names):
            raise ValueError(
                "Plugin name and aliases must be unique."
            )

        if not self.version.strip():
            raise ValueError(
                "Plugin version cannot be empty."
            )