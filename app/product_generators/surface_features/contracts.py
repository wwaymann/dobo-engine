from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


Point2D = tuple[float, float]


class TopologyRole(str, Enum):
    OUTER = "outer"
    HOLE = "hole"
    ISLAND = "island"


@dataclass(frozen=True, slots=True)
class TopologyLoop:
    id: str
    points: tuple[Point2D, ...]
    signed_area: float
    depth: int
    role: TopologyRole
    parent_id: str | None = None

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("TopologyLoop id cannot be empty.")

        if not isinstance(self.points, tuple) or len(self.points) < 3:
            raise ValueError(
                "TopologyLoop requires at least three points."
            )

        if isinstance(self.depth, bool) or not isinstance(
            self.depth,
            int,
        ):
            raise TypeError("TopologyLoop depth must be an integer.")

        if self.depth < 0:
            raise ValueError(
                "TopologyLoop depth cannot be negative."
            )

        if not isinstance(
            self.role,
            TopologyRole,
        ):
            raise TypeError(
                "TopologyLoop role must be TopologyRole."
            )

        if self.parent_id is not None:
            if (
                not isinstance(
                    self.parent_id,
                    str,
                )
                or not self.parent_id.strip()
            ):
                raise ValueError(
                    "TopologyLoop parent_id must be "
                    "a non-empty string or None."
                )


@dataclass(frozen=True, slots=True)
class TopologyDocument:
    id: str
    loops: tuple[TopologyLoop, ...]

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError(
                "TopologyDocument id cannot be empty."
            )

        if not isinstance(self.loops, tuple):
            raise TypeError(
                "TopologyDocument loops must be a tuple."
            )

        if not self.loops:
            raise ValueError(
                "TopologyDocument must contain loops."
            )

        ids: set[str] = set()

        for loop in self.loops:
            if not isinstance(
                loop,
                TopologyLoop,
            ):
                raise TypeError(
                    "TopologyDocument accepts "
                    "TopologyLoop values only."
                )

            loop.validate()

            if loop.id in ids:
                raise ValueError(
                    f"Duplicate topology loop id '{loop.id}'."
                )

            ids.add(loop.id)

    @property
    def outer_loops(
        self,
    ) -> tuple[TopologyLoop, ...]:
        return tuple(
            loop
            for loop in self.loops
            if loop.role is TopologyRole.OUTER
        )

    @property
    def holes(
        self,
    ) -> tuple[TopologyLoop, ...]:
        return tuple(
            loop
            for loop in self.loops
            if loop.role is TopologyRole.HOLE
        )

    @property
    def islands(
        self,
    ) -> tuple[TopologyLoop, ...]:
        return tuple(
            loop
            for loop in self.loops
            if loop.role is TopologyRole.ISLAND
        )
