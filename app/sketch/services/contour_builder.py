"""
DOBO Sketch

Sketch Contour Builder

Converts Sketch entities into backend-independent
Kernel ContourDefinition contracts.
"""

from __future__ import annotations

import math

from kernel.contracts.contour_definition import (
    ContourDefinition,
)
from kernel.contracts.contour_definition_set import (
    ContourDefinitionSet,
)
from sketch.entities import (
    CircleEntity,
    PolylineEntity,
)
from sketch.sketch import Sketch


class SketchContourBuilder:
    """
    Converts closed sketch entities into contours.

    Supported entities:

    - CircleEntity
    - closed PolylineEntity

    LineEntity objects are not converted individually,
    because isolated lines do not define closed profiles.
    """

    def build(
        self,
        sketch: Sketch,
        *,
        circle_samples: int = 64,
    ) -> ContourDefinitionSet:
        """
        Converts one Sketch into ContourDefinitionSet.
        """

        if not isinstance(
            sketch,
            Sketch,
        ):
            raise TypeError(
                "SketchContourBuilder requires "
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
                "circle_samples must be an integer."
            )

        if circle_samples < 16:
            raise ValueError(
                "circle_samples must be at least 16."
            )

        contours: list[
            ContourDefinition
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
                contours.append(
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
                if not entity.closed:
                    continue

                contours.append(
                    self._build_polyline(
                        entity
                    )
                )

        if not contours:
            raise ValueError(
                "Sketch does not contain usable "
                "closed profile entities."
            )

        result = ContourDefinitionSet(
            contours=tuple(
                contours
            ),
            source="sketch",
            metadata={
                "sketch_id": sketch.id,
                "sketch_name": sketch.name,
                "entity_count": sketch.count,
                "contour_count": len(
                    contours
                ),
                "circle_samples": circle_samples,
                **sketch.metadata,
            },
        )

        result.validate()

        return result

    @staticmethod
    def _build_polyline(
        entity: PolylineEntity,
    ) -> ContourDefinition:
        """
        Converts one closed polyline.
        """

        entity.validate()

        if not entity.closed:
            raise ValueError(
                "Only closed PolylineEntity objects "
                "can become contours."
            )

        result = ContourDefinition(
            points=tuple(
                point.tuple
                for point in entity.points
            ),
            closed=True,
            source="sketch_polyline",
            metadata={
                "entity_id": entity.id,
                "entity_type": (
                    entity.entity_type.value
                ),
                **entity.metadata,
            },
        )

        result.validate()

        return result

    @staticmethod
    def _build_circle(
        *,
        entity: CircleEntity,
        samples: int,
    ) -> ContourDefinition:
        """
        Samples one circle into ordered points.
        """

        entity.validate()

        points = tuple(
            (
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

        result = ContourDefinition(
            points=points,
            closed=True,
            source="sketch_circle",
            metadata={
                "entity_id": entity.id,
                "entity_type": (
                    entity.entity_type.value
                ),
                "radius": entity.radius,
                "samples": samples,
                **entity.metadata,
            },
        )

        result.validate()

        return result