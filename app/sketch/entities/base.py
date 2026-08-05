"""
DOBO Sketch

Base Sketch Entity

Defines the common fields shared by all sketch entities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class SketchEntityType(str, Enum):
    """
    Entity types currently supported by DOBO Sketch.
    """

    LINE = "line"
    CIRCLE = "circle"
    POLYLINE = "polyline"


@dataclass(frozen=True, slots=True)
class SketchEntity(ABC):
    """
    Common immutable sketch entity data.
    """

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    construction: bool = False

    enabled: bool = True

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates common entity fields.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "SketchEntity id cannot be empty."
            )

        if not isinstance(
            self.construction,
            bool,
        ):
            raise TypeError(
                "SketchEntity construction "
                "must be boolean."
            )

        if not isinstance(
            self.enabled,
            bool,
        ):
            raise TypeError(
                "SketchEntity enabled "
                "must be boolean."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "SketchEntity metadata "
                "must be a dictionary."
            )

    @property
    @abstractmethod
    def entity_type(self) -> SketchEntityType:
        """
        Returns the concrete entity type.
        """

    @property
    @abstractmethod
    def point_count(self) -> int:
        """
        Returns the number of defining points.
        """