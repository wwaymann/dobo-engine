"""
DOBO CAD Kernel

ModelState Contract

Represents the current geometric state of the model
while it moves through the Kernel pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .solid import Solid


@dataclass(frozen=True, slots=True)
class ModelHistoryEntry:
    """
    Represents one immutable change applied
    to the ModelState.
    """

    operation: str

    source_id: str = ""

    label: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the history entry.
        """

        if not self.operation.strip():
            raise ValueError(
                "ModelHistoryEntry operation cannot be empty."
            )


@dataclass(frozen=True, slots=True)
class ModelState:
    """
    Represents the current solid model.

    ModelState is immutable. Every Boolean Engine
    operation returns a new ModelState.
    """

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    solid: Solid | None = None

    history: tuple[
        ModelHistoryEntry,
        ...,
    ] = ()

    version: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete ModelState.
        """

        if self.version < 0:
            raise ValueError(
                "ModelState version cannot be negative."
            )

        if self.solid is not None:
            self.solid.validate()

        for history_entry in self.history:
            history_entry.validate()

    @property
    def is_empty(self) -> bool:
        """
        Returns True when the ModelState
        does not yet contain a Solid.
        """

        return self.solid is None

    @property
    def operation_count(self) -> int:
        """
        Returns the number of recorded operations.
        """

        return len(self.history)

    def with_solid(
        self,
        solid: Solid,
        operation: str,
        source_id: str = "",
        label: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "ModelState":
        """
        Returns a new ModelState containing
        the supplied Solid and history entry.
        """

        solid.validate()

        history_entry = ModelHistoryEntry(
            operation=operation,
            source_id=source_id,
            label=label,
            metadata=(
                metadata.copy()
                if metadata is not None
                else {}
            ),
        )

        history_entry.validate()

        return ModelState(
            solid=solid,
            history=(
                *self.history,
                history_entry,
            ),
            version=self.version + 1,
            metadata=self.metadata.copy(),
        )

    def with_metadata(
        self,
        **values: Any,
    ) -> "ModelState":
        """
        Returns a new ModelState with updated metadata.
        """

        updated_metadata = self.metadata.copy()
        updated_metadata.update(values)

        return ModelState(
            solid=self.solid,
            history=self.history,
            version=self.version,
            metadata=updated_metadata,
        )