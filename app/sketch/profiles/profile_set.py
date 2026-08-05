"""
DOBO Sketch

Profile Set

Represents a validated collection of closed profiles
produced by the Sketch Profile Builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .profile import (
    Bounds2D,
    Profile,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProfileSet:
    """
    Immutable collection of Profiles.

    Produced by ProfileBuilder and consumed by
    subsequent Sketch and Feature stages.
    """

    profiles: tuple[
        Profile,
        ...
    ]

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    source_sketch_id: str | None = None

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(
        self,
    ) -> None:
        """
        Validates the complete ProfileSet.
        """

        if (
            not isinstance(
                self.id,
                str,
            )
            or not self.id.strip()
        ):
            raise ValueError(
                "ProfileSet id cannot be empty."
            )

        if not isinstance(
            self.profiles,
            tuple,
        ):
            raise TypeError(
                "ProfileSet profiles "
                "must be a tuple."
            )

        if len(
            self.profiles
        ) == 0:
            raise ValueError(
                "ProfileSet cannot be empty."
            )

        profile_ids: set[
            str
        ] = set()

        for profile in self.profiles:

            if not isinstance(
                profile,
                Profile,
            ):
                raise TypeError(
                    "ProfileSet must contain "
                    "Profile objects."
                )

            profile.validate()

            if (
                profile.id
                in profile_ids
            ):
                raise ValueError(
                    "Duplicate Profile id "
                    f"'{profile.id}'."
                )

            profile_ids.add(
                profile.id
            )

        if (
            self.source_sketch_id
            is not None
        ):
            if (
                not isinstance(
                    self.source_sketch_id,
                    str,
                )
                or not self.source_sketch_id.strip()
            ):
                raise ValueError(
                    "source_sketch_id "
                    "must be a non-empty string."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "metadata must "
                "be a dictionary."
            )

    @property
    def count(
        self,
    ) -> int:
        """
        Number of profiles.
        """

        return len(
            self.profiles
        )

    @property
    def point_count(
        self,
    ) -> int:
        """
        Total profile points.
        """

        return sum(
            profile.point_count
            for profile
            in self.profiles
        )

    @property
    def total_area(
        self,
    ) -> float:
        """
        Sum of profile areas.
        """

        return sum(
            profile.area
            for profile
            in self.profiles
        )

    @property
    def total_perimeter(
        self,
    ) -> float:
        """
        Sum of profile perimeters.
        """

        return sum(
            profile.perimeter
            for profile
            in self.profiles
        )

    @property
    def bounds(
        self,
    ) -> Bounds2D:
        """
        Returns global ProfileSet bounds.
        """

        minimum_x = min(
            profile.bounds[0][0]
            for profile
            in self.profiles
        )

        minimum_y = min(
            profile.bounds[0][1]
            for profile
            in self.profiles
        )

        maximum_x = max(
            profile.bounds[1][0]
            for profile
            in self.profiles
        )

        maximum_y = max(
            profile.bounds[1][1]
            for profile
            in self.profiles
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
    def outer_profiles(
        self,
    ) -> tuple[
        Profile,
        ...
    ]:
        """
        Profiles with CCW orientation.
        """

        return tuple(
            profile
            for profile
            in self.profiles
            if profile.counterclockwise
        )

    @property
    def inner_profiles(
        self,
    ) -> tuple[
        Profile,
        ...
    ]:
        """
        Profiles with CW orientation.
        """

        return tuple(
            profile
            for profile
            in self.profiles
            if profile.clockwise
        )

    @property
    def largest_profile(
        self,
    ) -> Profile:
        """
        Returns the largest profile.
        """

        return max(
            self.profiles,
            key=lambda profile: profile.area,
        )

    def contains_point(
        self,
        point,
    ) -> bool:
        """
        Returns whether any profile
        contains the supplied point.
        """

        return any(
            profile.contains_point(
                point
            )
            for profile
            in self.profiles
        )

    def profile_by_id(
        self,
        profile_id: str,
    ) -> Profile:
        """
        Returns one profile.
        """

        for profile in self.profiles:

            if (
                profile.id
                == profile_id
            ):
                return profile

        raise KeyError(
            f"Unknown Profile '{profile_id}'."
        )