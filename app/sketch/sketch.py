"""
DOBO Sketch

Sketch Contract

Stores an ordered collection of backend-independent
two-dimensional sketch entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .entities import (
    CircleEntity,
    LineEntity,
    PolylineEntity,
    SketchEntityValue,
)


Bounds2D = tuple[
    tuple[float, float],
    tuple[float, float],
]


@dataclass(slots=True)
class Sketch:
    """
    Mutable sketch definition.

    Geometry remains independent from CadQuery.
    """

    id: str = field(
        default_factory=lambda: str(uuid4())
    )
    name: str = ""
    entities: list[SketchEntityValue] = field(
        default_factory=list
    )
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def add_entity(
        self,
        entity: SketchEntityValue,
    ) -> None:
        """Adds one validated entity."""

        self._validate_entity(entity)

        if self.has_entity(entity.id):
            raise ValueError(
                "Sketch already contains entity "
                f"'{entity.id}'."
            )

        self.entities.append(entity)

    def remove_entity(
        self,
        entity_id: str,
    ) -> SketchEntityValue:
        """Removes and returns one entity."""

        return self.entities.pop(
            self.index_of(entity_id)
        )

    def get_entity(
        self,
        entity_id: str,
    ) -> SketchEntityValue:
        """Returns one entity by identifier."""

        normalized = self._normalize_id(entity_id)

        for entity in self.entities:
            if entity.id == normalized:
                return entity

        raise KeyError(
            "Sketch does not contain entity "
            f"'{normalized}'."
        )

    def index_of(
        self,
        entity_id: str,
    ) -> int:
        """Returns one entity index."""

        normalized = self._normalize_id(entity_id)

        for index, entity in enumerate(self.entities):
            if entity.id == normalized:
                return index

        raise KeyError(
            "Sketch does not contain entity "
            f"'{normalized}'."
        )

    def has_entity(
        self,
        entity_id: str,
    ) -> bool:
        """Returns whether an entity ID exists."""

        normalized = self._normalize_id(entity_id)

        return any(
            entity.id == normalized
            for entity in self.entities
        )

    def validate(self) -> None:
        """Validates the complete sketch."""

        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError(
                "Sketch id cannot be empty."
            )

        if not isinstance(self.name, str):
            raise TypeError(
                "Sketch name must be a string."
            )

        if not isinstance(self.entities, list):
            raise TypeError(
                "Sketch entities must be a list."
            )

        if not isinstance(self.metadata, dict):
            raise TypeError(
                "Sketch metadata must be a dictionary."
            )

        entity_ids: set[str] = set()

        for entity in self.entities:
            self._validate_entity(entity)

            if entity.id in entity_ids:
                raise ValueError(
                    "Sketch contains duplicate "
                    f"entity id '{entity.id}'."
                )

            entity_ids.add(entity.id)

    @property
    def count(self) -> int:
        return len(self.entities)

    @property
    def enabled_count(self) -> int:
        return sum(
            1
            for entity in self.entities
            if entity.enabled
        )

    @property
    def construction_count(self) -> int:
        return sum(
            1
            for entity in self.entities
            if entity.construction
        )

    @property
    def line_count(self) -> int:
        return sum(
            1
            for entity in self.entities
            if isinstance(entity, LineEntity)
        )

    @property
    def circle_count(self) -> int:
        return sum(
            1
            for entity in self.entities
            if isinstance(entity, CircleEntity)
        )

    @property
    def polyline_count(self) -> int:
        return sum(
            1
            for entity in self.entities
            if isinstance(entity, PolylineEntity)
        )

    @property
    def bounds(self) -> Bounds2D | None:
        """Returns bounds for enabled geometry."""

        coordinates: list[tuple[float, float]] = []

        for entity in self.entities:
            if not entity.enabled:
                continue

            if isinstance(entity, LineEntity):
                coordinates.extend(
                    (
                        entity.start.tuple,
                        entity.end.tuple,
                    )
                )

            elif isinstance(entity, CircleEntity):
                coordinates.extend(
                    (
                        (
                            entity.center.x - entity.radius,
                            entity.center.y - entity.radius,
                        ),
                        (
                            entity.center.x + entity.radius,
                            entity.center.y + entity.radius,
                        ),
                    )
                )

            elif isinstance(entity, PolylineEntity):
                coordinates.extend(
                    point.tuple
                    for point in entity.points
                )

        if not coordinates:
            return None

        all_x = tuple(point[0] for point in coordinates)
        all_y = tuple(point[1] for point in coordinates)

        return (
            (min(all_x), min(all_y)),
            (max(all_x), max(all_y)),
        )

    @staticmethod
    def _validate_entity(
        entity: SketchEntityValue,
    ) -> None:
        if not isinstance(
            entity,
            (
                LineEntity,
                CircleEntity,
                PolylineEntity,
            ),
        ):
            raise TypeError(
                "Sketch supports LineEntity, CircleEntity "
                "and PolylineEntity only."
            )

        entity.validate()

    @staticmethod
    def _normalize_id(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "Sketch entity id must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Sketch entity id cannot be empty."
            )

        return normalized
