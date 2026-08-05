"""
DOBO Sketch

Region Set Contract

Stores a validated collection of independent sketch
regions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sketch.entities import SketchPoint

from .region import Region


@dataclass(frozen=True, slots=True)
class RegionSet:
    """
    Immutable collection of topological regions.
    """

    regions: tuple[
        Region,
        ...,
    ]

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    source_profile_set_id: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete RegionSet.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "RegionSet id cannot be empty."
            )

        if not isinstance(
            self.regions,
            tuple,
        ):
            raise TypeError(
                "RegionSet regions must be "
                "a tuple."
            )

        if not self.regions:
            raise ValueError(
                "RegionSet cannot be empty."
            )

        region_ids: set[str] = set()
        outer_profile_ids: set[str] = set()

        for region in self.regions:
            if not isinstance(
                region,
                Region,
            ):
                raise TypeError(
                    "RegionSet must contain "
                    "Region objects."
                )

            region.validate()

            if region.id in region_ids:
                raise ValueError(
                    "RegionSet contains duplicate "
                    f"region id '{region.id}'."
                )

            region_ids.add(
                region.id
            )

            outer_id = (
                region.outer_profile.id
            )

            if outer_id in outer_profile_ids:
                raise ValueError(
                    "A Profile cannot be the outer "
                    "boundary of multiple Regions."
                )

            outer_profile_ids.add(
                outer_id
            )

        if self.source_profile_set_id is not None:
            if not isinstance(
                self.source_profile_set_id,
                str,
            ) or not self.source_profile_set_id.strip():
                raise ValueError(
                    "RegionSet source_profile_set_id "
                    "must be a non-empty string."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "RegionSet metadata must be "
                "a dictionary."
            )

    @property
    def count(self) -> int:
        return len(
            self.regions
        )

    @property
    def hole_count(self) -> int:
        return sum(
            region.hole_count
            for region in self.regions
        )

    @property
    def profile_count(self) -> int:
        return sum(
            region.profile_count
            for region in self.regions
        )

    @property
    def total_area(self) -> float:
        return sum(
            region.area
            for region in self.regions
        )

    @property
    def total_perimeter(self) -> float:
        return sum(
            region.perimeter
            for region in self.regions
        )

    @property
    def bounds(
        self,
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
    ]:
        minimum_x = min(
            region.bounds[0][0]
            for region in self.regions
        )

        minimum_y = min(
            region.bounds[0][1]
            for region in self.regions
        )

        maximum_x = max(
            region.bounds[1][0]
            for region in self.regions
        )

        maximum_y = max(
            region.bounds[1][1]
            for region in self.regions
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

    @property
    def largest_region(self) -> Region:
        return max(
            self.regions,
            key=lambda region: region.area,
        )

    def region_by_id(
        self,
        region_id: str,
    ) -> Region:
        if not isinstance(
            region_id,
            str,
        ) or not region_id.strip():
            raise ValueError(
                "Region id must be a "
                "non-empty string."
            )

        for region in self.regions:
            if region.id == region_id:
                return region

        raise KeyError(
            f"Unknown Region '{region_id}'."
        )

    def contains_point(
        self,
        point: SketchPoint,
    ) -> bool:
        return any(
            region.contains_point(
                point
            )
            for region in self.regions
        )
