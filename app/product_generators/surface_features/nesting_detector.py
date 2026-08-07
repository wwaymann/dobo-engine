from __future__ import annotations

from dataclasses import dataclass

from product_generators.vector_geometry.contracts import (
    VectorContour,
)

from .geometry2d import (
    bounding_box,
    box_contains_box,
    point_in_polygon,
    representative_point,
)


@dataclass(frozen=True, slots=True)
class NestingRelation:
    child_id: str
    parent_id: str | None
    depth: int


class ContourNestingDetector:
    """
    Determines contour parent-child nesting.
    """

    def detect(
        self,
        contours: tuple[
            VectorContour,
            ...,
        ],
    ) -> tuple[
        NestingRelation,
        ...,
    ]:
        if not contours:
            raise ValueError(
                "Contours cannot be empty."
            )

        for contour in contours:
            contour.validate()

            if not contour.closed:
                raise ValueError(
                    "Topology nesting requires "
                    "closed contours."
                )

        boxes = {
            contour.id: bounding_box(
                contour.points
            )
            for contour in contours
        }

        relation_map: dict[
            str,
            str | None,
        ] = {}

        area_map = {
            contour.id: abs(
                self._polygon_area(
                    contour.points
                )
            )
            for contour in contours
        }

        for child in contours:
            sample = (
                representative_point(
                    child.points
                )
            )

            containers: list[
                VectorContour
            ] = []

            for candidate in contours:
                if (
                    candidate.id
                    == child.id
                ):
                    continue

                if not box_contains_box(
                    boxes[candidate.id],
                    boxes[child.id],
                ):
                    continue

                if point_in_polygon(
                    sample,
                    candidate.points,
                ):
                    containers.append(
                        candidate
                    )

            if containers:
                parent = min(
                    containers,
                    key=lambda contour: (
                        area_map[
                            contour.id
                        ]
                    ),
                )

                relation_map[
                    child.id
                ] = parent.id

            else:
                relation_map[
                    child.id
                ] = None

        def depth_for(
            contour_id: str,
        ) -> int:
            depth = 0
            parent_id = (
                relation_map[
                    contour_id
                ]
            )

            visited = {
                contour_id
            }

            while parent_id is not None:
                if parent_id in visited:
                    raise RuntimeError(
                        "Cyclic contour nesting "
                        "was detected."
                    )

                visited.add(
                    parent_id
                )

                depth += 1

                parent_id = (
                    relation_map[
                        parent_id
                    ]
                )

            return depth

        return tuple(
            NestingRelation(
                child_id=contour.id,
                parent_id=relation_map[
                    contour.id
                ],
                depth=depth_for(
                    contour.id
                ),
            )
            for contour in contours
        )

    @staticmethod
    def _polygon_area(
        points,
    ) -> float:
        total = 0.0

        for index, point in enumerate(
            points
        ):
            next_point = points[
                (index + 1)
                % len(points)
            ]

            total += (
                point[0]
                * next_point[1]
                - next_point[0]
                * point[1]
            )

        return total / 2.0
