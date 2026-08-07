from __future__ import annotations

from .contracts import (
    TopologyRole,
)


class ContourRoleClassifier:
    """
    Uses even-odd nesting depth semantics.

    depth 0 -> OUTER
    depth 1 -> HOLE
    depth 2 -> ISLAND
    depth 3 -> HOLE
    depth 4 -> ISLAND
    ...
    """

    @staticmethod
    def classify(
        depth: int,
    ) -> TopologyRole:
        if isinstance(
            depth,
            bool,
        ) or not isinstance(
            depth,
            int,
        ):
            raise TypeError(
                "depth must be an integer."
            )

        if depth < 0:
            raise ValueError(
                "depth cannot be negative."
            )

        if depth == 0:
            return TopologyRole.OUTER

        if depth % 2 == 1:
            return TopologyRole.HOLE

        return TopologyRole.ISLAND
