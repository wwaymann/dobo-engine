"""
DOBO CAD Kernel

Region Definition Provider

Converts Sketch Region topology into backend-independent
GeometryDefinition contracts.
"""

from __future__ import annotations

from kernel.contracts.contour_definition import (
    ContourDefinition,
)
from kernel.contracts.geometry_definition import (
    GeometryDefinition,
)
from kernel.contracts.geometry_definition_set import (
    GeometryDefinitionSet,
)
from sketch.profiles.profile import Profile
from sketch.topology.region import Region
from sketch.topology.region_set import RegionSet


class RegionDefinitionProvider:
    """
    Converts Region and RegionSet objects into Kernel
    geometry definitions.

    This provider does not create CadQuery or
    OpenCascade geometry.
    """

    @property
    def name(self) -> str:
        return "region_definition"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return (
            "Converts Sketch Regions into "
            "backend-independent geometry definitions."
        )

    def execute(
        self,
        regions: RegionSet,
    ) -> GeometryDefinitionSet:
        """
        Converts one RegionSet.
        """

        if not isinstance(
            regions,
            RegionSet,
        ):
            raise TypeError(
                "RegionDefinitionProvider requires "
                "a RegionSet."
            )

        regions.validate()

        definitions = tuple(
            self._build_region_definition(
                region
            )
            for region in regions.regions
        )

        result = GeometryDefinitionSet(
            definitions=definitions,
            source=self.name,
            metadata={
                "provider": self.name,
                "provider_version": self.version,
                "source_region_set_id": regions.id,
                "region_count": regions.count,
                "hole_count": regions.hole_count,
                **regions.metadata,
            },
        )

        result.validate()

        return result

    def _build_region_definition(
        self,
        region: Region,
    ) -> GeometryDefinition:
        """
        Converts one Region.
        """

        region.validate()

        outer = self._build_contour(
            profile=region.outer_profile,
            role="outer",
        )

        inner = tuple(
            self._build_contour(
                profile=profile,
                role="inner",
            )
            for profile in region.inner_profiles
        )

        result = GeometryDefinition(
            outer_contour=outer,
            inner_contours=inner,
            source=self.name,
            metadata={
                "source_region_id": region.id,
                "hole_count": region.hole_count,
                "region_area": region.area,
                **region.metadata,
            },
        )

        result.validate()

        return result

    def _build_contour(
        self,
        *,
        profile: Profile,
        role: str,
    ) -> ContourDefinition:
        """
        Converts one Profile into ContourDefinition.
        """

        profile.validate()

        contour = ContourDefinition(
            points=profile.tuples,
            closed=True,
            source=self.name,
            metadata={
                "source_profile_id": profile.id,
                "source_entity_ids": (
                    profile.source_entity_ids
                ),
                "role": role,
                "clockwise": profile.clockwise,
                **profile.metadata,
            },
        )

        contour.validate()

        return contour
