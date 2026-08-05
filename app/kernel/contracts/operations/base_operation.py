"""
DOBO CAD Kernel

Base Operation Contract

Defines the common immutable data shared by every
operation executed by the Kernel Core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class OperationType(str, Enum):
    """
    Operation types understood by the Kernel Core.
    """

    GEOMETRY = "geometry"
    BOOLEAN = "boolean"
    EXPORT = "export"


@dataclass(frozen=True, slots=True)
class BaseOperation:
    """
    Common immutable operation data.

    Specialized operations inherit from this contract.
    """

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    name: str = ""

    enabled: bool = True

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates common operation fields.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "Operation id cannot be empty."
            )

        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "Operation name must be a string."
            )

        if not isinstance(
            self.enabled,
            bool,
        ):
            raise TypeError(
                "Operation enabled must be boolean."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "Operation metadata must be a dictionary."
            )

    @property
    def operation_type(self) -> OperationType:
        """
        Returns the concrete operation type.

        Specialized contracts must override this property.
        """

        raise NotImplementedError(
            "BaseOperation does not define "
            "a concrete operation type."
        )

    @property
    def display_name(self) -> str:
        """
        Returns a readable operation name.
        """

        normalized_name = self.name.strip()

        if normalized_name:
            return normalized_name

        return self.operation_type.value

    @property
    def is_enabled(self) -> bool:
        """
        Returns whether the operation must execute.
        """

        return self.enabled