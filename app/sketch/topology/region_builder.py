"""
DOBO Sketch

Region Builder

Builds topological Regions from a ProfileSet by analyzing
profile containment relationships.
"""

from __future__ import annotations

from dataclasses import dataclass

from sketch.entities import SketchPoint
from sketch.profiles.profile import Profile
from sketch.profiles.profile_set import ProfileSet

from .region import Region
from .region_set import RegionSet


@dataclass(frozen=True, slots=True)
class _ProfileTopology:
    profile: Profile
    parent_id: str | None
    depth: int


class RegionBuilder:
    """
    Builds Regions using even-odd containment topology.

    Depth 0, 2, 4... profiles become outer boundaries.
    Their direct odd-depth children become holes.

    Example:

    outer rectangle       depth 0 -> Region outer
    inner circle          depth 1 -> hole
    island inside circle  depth 2 -> new Region outer
    """

    def build(
        self,
        profiles: ProfileSet,
    ) -> RegionSet:
        """
        Converts one ProfileSet into RegionSet.
        """

        if not isinstance(
            profiles,
            ProfileSet,
        ):
            raise TypeError(
                "RegionBuilder requires "
                "a ProfileSet."
            )

        profiles.validate()

        topology = self._build_topology(
            profiles
        )

        by_parent: dict[
            str | None,
            list[_ProfileTopology],
        ] = {}

        for item in topology:
            by_parent.setdefault(
                item.parent_id,
                [],
            ).append(
                item
            )

        regions: list[Region] = []

        for item in topology:
            if item.depth % 2 != 0:
                continue

            children = by_parent.get(
                item.profile.id,
                [],
            )

            holes = tuple(
                child.profile
                for child in children
                if child.depth == (
                    item.depth + 1
                )
            )

            outer = self._ensure_orientation(
                item.profile,
                clockwise=False,
            )

            oriented_holes = tuple(
                self._ensure_orientation(
                    hole,
                    clockwise=True,
                )
                for hole in holes
            )

            region = Region(
                outer_profile=outer,
                inner_profiles=oriented_holes,
                metadata={
                    "source": "region_builder",
                    "depth": item.depth,
                    "parent_profile_id": (
                        item.parent_id
                    ),
                },
            )

            region.validate()

            regions.append(
                region
            )

        if not regions:
            raise ValueError(
                "RegionBuilder could not produce "
                "any Regions."
            )

        result = RegionSet(
            regions=tuple(
                regions
            ),
            source_profile_set_id=profiles.id,
            metadata={
                "profile_count": profiles.count,
                "region_count": len(
                    regions
                ),
                "hole_count": sum(
                    region.hole_count
                    for region in regions
                ),
                **profiles.metadata,
            },
        )

        result.validate()

        return result

    def _build_topology(
        self,
        profiles: ProfileSet,
    ) -> tuple[
        _ProfileTopology,
        ...,
    ]:
        """
        Calculates direct parent and nesting depth.
        """

        ordered = tuple(
            sorted(
                profiles.profiles,
                key=lambda profile: (
                    -profile.area
                ),
            )
        )

        parent_by_id: dict[
            str,
            str | None,
        ] = {}

        depth_by_id: dict[
            str,
            int,
        ] = {}

        for index, profile in enumerate(
            ordered
        ):
            sample = self._sample_point(
                profile
            )

            containing = [
                candidate
                for candidate in ordered[
                    :index
                ]
                if candidate.contains_point(
                    sample
                )
            ]

            if not containing:
                parent_by_id[
                    profile.id
                ] = None

                depth_by_id[
                    profile.id
                ] = 0

                continue

            parent = min(
                containing,
                key=lambda candidate: (
                    candidate.area
                ),
            )

            parent_by_id[
                profile.id
            ] = parent.id

            depth_by_id[
                profile.id
            ] = (
                depth_by_id[
                    parent.id
                ]
                + 1
            )

        return tuple(
            _ProfileTopology(
                profile=profile,
                parent_id=parent_by_id[
                    profile.id
                ],
                depth=depth_by_id[
                    profile.id
                ],
            )
            for profile in ordered
        )

    @staticmethod
    def _sample_point(
        profile: Profile,
    ) -> SketchPoint:
        """
        Returns a representative point for containment.
        """

        x, y = profile.centroid

        return SketchPoint(
            x,
            y,
        )

    @staticmethod
    def _ensure_orientation(
        profile: Profile,
        *,
        clockwise: bool,
    ) -> Profile:
        """
        Normalizes profile orientation.
        """

        if clockwise:
            if profile.clockwise:
                return profile

            return profile.reversed()

        if profile.counterclockwise:
            return profile

        return profile.reversed()
