"""
DOBO Sketch

Line Profile Recognizer

Detects closed profiles formed by independent
LineEntity objects.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sketch.entities import (
    LineEntity,
    SketchPoint,
)

from .profile import Profile


PointKey = tuple[int, int]


@dataclass(frozen=True, slots=True)
class LineProfileRecognitionResult:
    """
    Result produced by LineProfileRecognizer.
    """

    profiles: tuple[Profile, ...]

    used_entity_ids: tuple[str, ...]

    ignored_entity_ids: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(
            self.profiles
        )


class LineProfileRecognizer:
    """
    Recognizes closed loops formed by LineEntity objects.

    Current supported topology:

    - independent closed components;
    - every vertex in a recognized component must
      connect to exactly two lines;
    - endpoints may differ slightly within tolerance.

    Components with branches, gaps or isolated lines
    are ignored.
    """

    def recognize(
        self,
        lines: tuple[LineEntity, ...],
        *,
        tolerance: float = 1e-6,
    ) -> LineProfileRecognitionResult:
        """
        Detects closed line loops and converts them
        into Profile objects.
        """

        self._validate_input(
            lines=lines,
            tolerance=tolerance,
        )

        enabled_lines = tuple(
            line
            for line in lines
            if (
                line.enabled
                and not line.construction
            )
        )

        if not enabled_lines:
            return LineProfileRecognitionResult(
                profiles=(),
                used_entity_ids=(),
                ignored_entity_ids=(),
            )

        point_by_key: dict[
            PointKey,
            SketchPoint,
        ] = {}

        adjacency: dict[
            PointKey,
            list[
                tuple[
                    PointKey,
                    LineEntity,
                ]
            ],
        ] = defaultdict(
            list
        )

        for line in enabled_lines:
            line.validate()

            start_key = self._point_key(
                line.start,
                tolerance,
            )

            end_key = self._point_key(
                line.end,
                tolerance,
            )

            if start_key == end_key:
                continue

            point_by_key.setdefault(
                start_key,
                line.start,
            )

            point_by_key.setdefault(
                end_key,
                line.end,
            )

            adjacency[
                start_key
            ].append(
                (
                    end_key,
                    line,
                )
            )

            adjacency[
                end_key
            ].append(
                (
                    start_key,
                    line,
                )
            )

        components = self._build_components(
            adjacency
        )

        profiles: list[Profile] = []

        used_ids: set[str] = set()

        for component in components:
            component_profile = (
                self._build_component_profile(
                    component=component,
                    adjacency=adjacency,
                    point_by_key=point_by_key,
                )
            )

            if component_profile is None:
                continue

            profile, entity_ids = (
                component_profile
            )

            profiles.append(
                profile
            )

            used_ids.update(
                entity_ids
            )

        ignored_ids = tuple(
            line.id
            for line in enabled_lines
            if line.id not in used_ids
        )

        result = (
            LineProfileRecognitionResult(
                profiles=tuple(
                    profiles
                ),
                used_entity_ids=tuple(
                    sorted(
                        used_ids
                    )
                ),
                ignored_entity_ids=ignored_ids,
            )
        )

        return result

    def _build_component_profile(
        self,
        *,
        component: set[PointKey],
        adjacency: dict[
            PointKey,
            list[
                tuple[
                    PointKey,
                    LineEntity,
                ]
            ],
        ],
        point_by_key: dict[
            PointKey,
            SketchPoint,
        ],
    ) -> tuple[
        Profile,
        tuple[str, ...],
    ] | None:
        """
        Converts one graph component into a Profile
        when the component represents one simple cycle.
        """

        if len(
            component
        ) < 3:
            return None

        for key in component:
            connected_edges = [
                edge
                for edge in adjacency.get(
                    key,
                    []
                )
                if edge[0] in component
            ]

            if len(
                connected_edges
            ) != 2:
                return None

        start_key = min(
            component
        )

        ordered_keys: list[
            PointKey
        ] = [
            start_key
        ]

        ordered_entity_ids: list[str] = []

        previous_key: PointKey | None = None

        current_key = start_key

        visited_edges: set[
            tuple[
                PointKey,
                PointKey,
                str,
            ]
        ] = set()

        while True:
            candidates = []

            for next_key, line in adjacency[
                current_key
            ]:
                if next_key not in component:
                    continue

                if (
                    previous_key is not None
                    and next_key == previous_key
                ):
                    continue

                edge_key = self._edge_key(
                    current_key=current_key,
                    next_key=next_key,
                    entity_id=line.id,
                )

                if edge_key in visited_edges:
                    continue

                candidates.append(
                    (
                        next_key,
                        line,
                        edge_key,
                    )
                )

            if not candidates:
                if (
                    len(
                        ordered_keys
                    ) >= 3
                    and current_key
                    != start_key
                ):
                    closing_candidates = [
                        (
                            next_key,
                            line,
                            self._edge_key(
                                current_key=(
                                    current_key
                                ),
                                next_key=next_key,
                                entity_id=line.id,
                            ),
                        )
                        for next_key, line
                        in adjacency[
                            current_key
                        ]
                        if next_key == start_key
                    ]

                    if not closing_candidates:
                        return None

                    next_key, line, edge_key = (
                        closing_candidates[0]
                    )

                    visited_edges.add(
                        edge_key
                    )

                    ordered_entity_ids.append(
                        line.id
                    )

                    current_key = next_key

                break

            next_key, line, edge_key = (
                candidates[0]
            )

            visited_edges.add(
                edge_key
            )

            ordered_entity_ids.append(
                line.id
            )

            previous_key = current_key
            current_key = next_key

            if current_key == start_key:
                break

            if current_key in ordered_keys:
                return None

            ordered_keys.append(
                current_key
            )

            if len(
                ordered_keys
            ) > len(
                component
            ):
                return None

        if current_key != start_key:
            return None

        if len(
            ordered_keys
        ) != len(
            component
        ):
            return None

        if len(
            ordered_entity_ids
        ) != len(
            component
        ):
            return None

        points = tuple(
            point_by_key[
                key
            ]
            for key in ordered_keys
        )

        profile = Profile(
            points=points,
            source_entity_ids=tuple(
                ordered_entity_ids
            ),
            metadata={
                "source": (
                    "line_profile_recognizer"
                ),
                "line_count": len(
                    ordered_entity_ids
                ),
            },
        )

        profile.validate()

        return (
            profile,
            tuple(
                ordered_entity_ids
            ),
        )

    @staticmethod
    def _build_components(
        adjacency: dict[
            PointKey,
            list[
                tuple[
                    PointKey,
                    LineEntity,
                ]
            ],
        ],
    ) -> tuple[
        set[PointKey],
        ...,
    ]:
        """
        Finds connected graph components.
        """

        components: list[
            set[PointKey]
        ] = []

        visited: set[
            PointKey
        ] = set()

        for start_key in adjacency:
            if start_key in visited:
                continue

            component: set[
                PointKey
            ] = set()

            stack = [
                start_key
            ]

            while stack:
                current_key = stack.pop()

                if current_key in visited:
                    continue

                visited.add(
                    current_key
                )

                component.add(
                    current_key
                )

                for next_key, _ in adjacency[
                    current_key
                ]:
                    if next_key not in visited:
                        stack.append(
                            next_key
                        )

            components.append(
                component
            )

        return tuple(
            components
        )

    @staticmethod
    def _point_key(
        point: SketchPoint,
        tolerance: float,
    ) -> PointKey:
        """
        Converts a point into a tolerance-aware key.
        """

        return (
            round(
                point.x
                / tolerance
            ),
            round(
                point.y
                / tolerance
            ),
        )

    @staticmethod
    def _edge_key(
        *,
        current_key: PointKey,
        next_key: PointKey,
        entity_id: str,
    ) -> tuple[
        PointKey,
        PointKey,
        str,
    ]:
        """
        Creates a direction-independent edge key.
        """

        first, second = sorted(
            (
                current_key,
                next_key,
            )
        )

        return (
            first,
            second,
            entity_id,
        )

    @staticmethod
    def _validate_input(
        *,
        lines: tuple[
            LineEntity,
            ...,
        ],
        tolerance: float,
    ) -> None:
        """
        Validates recognizer input.
        """

        if not isinstance(
            lines,
            tuple,
        ):
            raise TypeError(
                "LineProfileRecognizer lines "
                "must be a tuple."
            )

        for line in lines:
            if not isinstance(
                line,
                LineEntity,
            ):
                raise TypeError(
                    "LineProfileRecognizer requires "
                    "LineEntity objects."
                )

            line.validate()

        if isinstance(
            tolerance,
            bool,
        ) or not isinstance(
            tolerance,
            (
                int,
                float,
            ),
        ):
            raise TypeError(
                "LineProfileRecognizer tolerance "
                "must be numeric."
            )

        if tolerance <= 0:
            raise ValueError(
                "LineProfileRecognizer tolerance "
                "must be greater than zero."
            )