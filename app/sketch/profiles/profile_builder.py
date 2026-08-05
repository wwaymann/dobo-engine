"""
DOBO Sketch

Profile Builder

Converts Sketch entities and connected line loops into
validated closed Profiles.
"""

from __future__ import annotations

import math

from sketch.entities import (
    CircleEntity,
    LineEntity,
    PolylineEntity,
    SketchPoint,
)
from sketch.sketch import Sketch

from .line_profile_recognizer import (
    LineProfileRecognizer,
)
from .profile import Profile
from .profile_set import ProfileSet


class ProfileBuilder:
    """
    Converts Sketch geometry into Profiles.

    Supported sources:

    - CircleEntity;
    - closed PolylineEntity;
    - closed cycles formed by LineEntity objects.
    """

    def __init__(
        self,
        line_recognizer: (
            LineProfileRecognizer
            | None
        ) = None,
    ) -> None:
        self._line_recognizer = (
            line_recognizer
            if line_recognizer
            is not None
            else LineProfileRecognizer()
        )

    def build(
        self,
        sketch: Sketch,
        *,
        circle_samples: int = 64,
        connection_tolerance: float = 1e-6,
    ) -> ProfileSet:
        """
        Builds a ProfileSet from one Sketch.
        """

        if not isinstance(
            sketch,
            Sketch,
        ):
            raise TypeError(
                "ProfileBuilder requires "
                "a Sketch."
            )

        sketch.validate()

        if isinstance(
            circle_samples,
            bool,
        ) or not isinstance(
            circle_samples,
            int,
        ):
            raise TypeError(
                "circle_samples must be "
                "an integer."
            )

        if circle_samples < 16:
            raise ValueError(
                "circle_samples must be >= 16."
            )

        profiles: list[
            Profile
        ] = []

        line_entities: list[
            LineEntity
        ] = []

        for entity in sketch.entities:
            if (
                not entity.enabled
                or entity.construction
            ):
                continue

            if isinstance(
                entity,
                CircleEntity,
            ):
                profiles.append(
                    self._build_circle(
                        entity=entity,
                        samples=circle_samples,
                    )
                )

                continue

            if isinstance(
                entity,
                PolylineEntity,
            ):
                if entity.closed:
                    profiles.append(
                        self._build_polyline(
                            entity
                        )
                    )

                continue

            if isinstance(
                entity,
                LineEntity,
            ):
                line_entities.append(
                    entity
                )

        line_result = (
            self._line_recognizer.recognize(
                tuple(
                    line_entities
                ),
                tolerance=(
                    connection_tolerance
                ),
            )
        )

        profiles.extend(
            line_result.profiles
        )

        if not profiles:
            raise ValueError(
                "Sketch does not contain "
                "closed profiles."
            )

        result = ProfileSet(
            profiles=tuple(
                profiles
            ),
            source_sketch_id=sketch.id,
            metadata={
                "entity_count": sketch.count,
                "profile_count": len(
                    profiles
                ),
                "circle_samples": circle_samples,
                "line_profiles": (
                    line_result.count
                ),
                "used_line_entity_ids": (
                    line_result.used_entity_ids
                ),
                "ignored_line_entity_ids": (
                    line_result.ignored_entity_ids
                ),
                **sketch.metadata,
            },
        )

        result.validate()

        return result

    @staticmethod
    def _build_polyline(
        entity: PolylineEntity,
    ) -> Profile:
        """
        Converts a closed PolylineEntity.
        """

        entity.validate()

        if not entity.closed:
            raise ValueError(
                "ProfileBuilder only converts "
                "closed PolylineEntity objects."
            )

        result = Profile(
            points=entity.points,
            source_entity_ids=(
                entity.id,
            ),
            metadata={
                **entity.metadata,
                "entity_type": "polyline",
            },
        )

        result.validate()

        return result

    @staticmethod
    def _build_circle(
        *,
        entity: CircleEntity,
        samples: int,
    ) -> Profile:
        """
        Samples one circle into a Profile.
        """

        entity.validate()

        points = tuple(
            SketchPoint(
                entity.center.x
                + entity.radius
                * math.cos(
                    (
                        2.0
                        * math.pi
                        * index
                    )
                    / samples
                ),
                entity.center.y
                + entity.radius
                * math.sin(
                    (
                        2.0
                        * math.pi
                        * index
                    )
                    / samples
                ),
            )
            for index in range(
                samples
            )
        )

        result = Profile(
            points=points,
            source_entity_ids=(
                entity.id,
            ),
            metadata={
                **entity.metadata,
                "entity_type": "circle",
                "radius": entity.radius,
                "samples": samples,
            },
        )

        result.validate()

        return result