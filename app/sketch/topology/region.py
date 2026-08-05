"""
DOBO Sketch

Region Contract

Represents one topological sketch region composed of
one outer profile and zero or more inner profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sketch.entities import SketchPoint
from sketch.profiles.profile import Profile


@dataclass(frozen=True, slots=True)
class Region:
    """
    Immutable topological region.

    outer_profile:
        Boundary that defines the filled exterior.

    inner_profiles:
        Boundaries that define holes.
    """

    outer_profile: Profile

    inner_profiles: tuple[
        Profile,
        ...,
    ] = ()

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete region topology.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "Region id cannot be empty."
            )

        if not isinstance(
            self.outer_profile,
            Profile,
        ):
            raise TypeError(
                "Region outer_profile must be "
                "a Profile."
            )

        self.outer_profile.validate()

        if not isinstance(
            self.inner_profiles,
            tuple,
        ):
            raise TypeError(
                "Region inner_profiles must be "
                "a tuple."
            )

        inner_ids: set[str] = set()

        for profile in self.inner_profiles:
            if not isinstance(
                profile,
                Profile,
            ):
                raise TypeError(
                    "Region inner_profiles must "
                    "contain Profile objects."
                )

            profile.validate()

            if profile.id == self.outer_profile.id:
                raise ValueError(
                    "Region cannot use its outer profile "
                    "as an inner profile."
                )

            if profile.id in inner_ids:
                raise ValueError(
                    "Region contains duplicate "
                    f"inner profile '{profile.id}'."
                )

            inner_ids.add(
                profile.id
            )

            sample = self._sample_point(
                profile
            )

            if not self.outer_profile.contains_point(
                sample
            ):
                raise ValueError(
                    "Region inner profile must be "
                    "contained by outer_profile."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "Region metadata must be "
                "a dictionary."
            )

        for index, first in enumerate(
            self.inner_profiles
        ):
            first_sample = self._sample_point(
                first
            )

            for second in self.inner_profiles[
                index + 1:
            ]:
                second_sample = self._sample_point(
                    second
                )

                if first.contains_point(
                    second_sample
                ) or second.contains_point(
                    first_sample
                ):
                    raise ValueError(
                        "Region inner profiles cannot "
                        "contain one another."
                    )

    @property
    def hole_count(self) -> int:
        """
        Returns the number of inner profiles.
        """

        return len(
            self.inner_profiles
        )

    @property
    def profile_count(self) -> int:
        """
        Returns outer plus inner profile count.
        """

        return 1 + self.hole_count

    @property
    def area(self) -> float:
        """
        Returns filled region area.
        """

        return (
            self.outer_profile.area
            - sum(
                profile.area
                for profile
                in self.inner_profiles
            )
        )

    @property
    def perimeter(self) -> float:
        """
        Returns total boundary length.
        """

        return (
            self.outer_profile.perimeter
            + sum(
                profile.perimeter
                for profile
                in self.inner_profiles
            )
        )

    @property
    def bounds(
        self,
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
    ]:
        """
        Returns outer-profile bounds.
        """

        return self.outer_profile.bounds

    @property
    def profiles(
        self,
    ) -> tuple[
        Profile,
        ...,
    ]:
        """
        Returns outer followed by inner profiles.
        """

        return (
            self.outer_profile,
            *self.inner_profiles,
        )

    def contains_point(
        self,
        point: SketchPoint,
    ) -> bool:
        """
        Returns whether a point lies in filled material.
        """

        if not isinstance(
            point,
            SketchPoint,
        ):
            raise TypeError(
                "Region.contains_point requires "
                "a SketchPoint."
            )

        point.validate()

        if not self.outer_profile.contains_point(
            point
        ):
            return False

        return not any(
            profile.contains_point(
                point
            )
            for profile
            in self.inner_profiles
        )

    @staticmethod
    def _sample_point(
        profile: Profile,
    ) -> SketchPoint:
        """
        Returns a representative interior point.
        """

        centroid_x, centroid_y = (
            profile.centroid
        )

        return SketchPoint(
            centroid_x,
            centroid_y,
        )
