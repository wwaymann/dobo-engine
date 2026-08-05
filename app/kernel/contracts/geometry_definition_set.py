"""
DOBO CAD Kernel

Geometry Definition Set Contract

Represents an immutable collection of planar
GeometryDefinition objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .geometry_definition import GeometryDefinition


@dataclass(frozen=True, slots=True)
class GeometryDefinitionSet:
    """
    Immutable collection of GeometryDefinition objects.
    """

    definitions: tuple[
        GeometryDefinition,
        ...,
    ]

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    source: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete collection.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "GeometryDefinitionSet id cannot be empty."
            )

        if not isinstance(
            self.definitions,
            tuple,
        ):
            raise TypeError(
                "GeometryDefinitionSet definitions "
                "must be a tuple."
            )

        if not self.definitions:
            raise ValueError(
                "GeometryDefinitionSet cannot be empty."
            )

        definition_ids: set[str] = set()

        for definition in self.definitions:
            if not isinstance(
                definition,
                GeometryDefinition,
            ):
                raise TypeError(
                    "GeometryDefinitionSet must contain "
                    "GeometryDefinition objects."
                )

            definition.validate()

            if definition.id in definition_ids:
                raise ValueError(
                    "GeometryDefinitionSet contains "
                    f"duplicate id '{definition.id}'."
                )

            definition_ids.add(
                definition.id
            )

        if not isinstance(
            self.source,
            str,
        ):
            raise TypeError(
                "GeometryDefinitionSet source "
                "must be a string."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "GeometryDefinitionSet metadata "
                "must be a dictionary."
            )

    @property
    def count(self) -> int:
        return len(
            self.definitions
        )

    @property
    def contour_count(self) -> int:
        return sum(
            definition.contour_count
            for definition in self.definitions
        )

    @property
    def hole_count(self) -> int:
        return sum(
            definition.hole_count
            for definition in self.definitions
        )

    @property
    def point_count(self) -> int:
        return sum(
            definition.point_count
            for definition in self.definitions
        )

    @property
    def bounds(
        self,
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
    ]:
        minimum_x = min(
            definition.bounds[0][0]
            for definition in self.definitions
        )

        minimum_y = min(
            definition.bounds[0][1]
            for definition in self.definitions
        )

        maximum_x = max(
            definition.bounds[1][0]
            for definition in self.definitions
        )

        maximum_y = max(
            definition.bounds[1][1]
            for definition in self.definitions
        )

        return (
            (
                minimum_x,
                minimum_y,
            ),
            (
                maximum_x,
                maximum_y,
            ),
        )

    def definition_by_id(
        self,
        definition_id: str,
    ) -> GeometryDefinition:
        if not isinstance(
            definition_id,
            str,
        ) or not definition_id.strip():
            raise ValueError(
                "GeometryDefinition id must be "
                "a non-empty string."
            )

        for definition in self.definitions:
            if definition.id == definition_id:
                return definition

        raise KeyError(
            f"Unknown GeometryDefinition "
            f"'{definition_id}'."
        )
