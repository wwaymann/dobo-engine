from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from .local_thickness import (
    LocalThicknessAnalyzer,
)
from .profile import ManufacturingProfile
from .report import (
    CheckStatus,
    ManufacturingCheck,
)


@dataclass(frozen=True, slots=True)
class SemanticManufacturingResult:
    body_check: ManufacturingCheck
    text_check: ManufacturingCheck
    decoration_check: ManufacturingCheck


class SemanticManufacturingAnalyzer:
    """
    Apply different manufacturing rules to semantically different regions.

    Body:
      wall-thickness analysis

    Text:
      connected printable volume + minimum volume proxy

    Decoration:
      connected printable volume + minimum volume proxy

    The purpose is to avoid interpreting decorative edge chords as body-wall
    thickness failures.
    """

    def analyze(
        self,
        *,
        body_region: cq.Shape,
        text_region: cq.Shape,
        decoration_region: cq.Shape,
        profile: ManufacturingProfile,
    ) -> SemanticManufacturingResult:
        profile.validate()

        return SemanticManufacturingResult(
            body_check=self._body_wall_check(
                body_region,
                profile,
            ),
            text_check=self._feature_region_check(
                shape=text_region,
                label="Text",
                code_prefix="TEXT",
                profile=profile,
            ),
            decoration_check=self._feature_region_check(
                shape=decoration_region,
                label="Decoration",
                code_prefix="DECORATION",
                profile=profile,
            ),
        )

    @staticmethod
    def _body_wall_check(
        shape: cq.Shape,
        profile: ManufacturingProfile,
    ) -> ManufacturingCheck:
        result = LocalThicknessAnalyzer().analyze(
            shape=shape,
            threshold=profile.min_wall_thickness,
            samples_per_axis=3,
        )

        if result.minimum is None:
            return ManufacturingCheck(
                code="BODY_WALL_INSUFFICIENT_SAMPLES",
                label="Body wall thickness",
                status=CheckStatus.WARNING,
                message=(
                    "Body wall analysis produced no usable local samples."
                ),
            )

        if result.minimum < profile.min_wall_thickness:
            return ManufacturingCheck(
                code="BODY_WALL_TOO_THIN",
                label="Body wall thickness",
                status=CheckStatus.WARNING,
                message=(
                    f"{result.thin_sample_count} of "
                    f"{result.sample_count} body samples are below "
                    "the preferred wall threshold."
                ),
                measured_value=result.minimum,
                required_value=profile.min_wall_thickness,
                unit="mm",
            )

        return ManufacturingCheck(
            code="BODY_WALL_OK",
            label="Body wall thickness",
            status=CheckStatus.OK,
            message=(
                f"{result.sample_count} body samples meet the "
                "minimum wall-thickness threshold."
            ),
            measured_value=result.minimum,
            required_value=profile.min_wall_thickness,
            unit="mm",
        )

    @staticmethod
    def _feature_region_check(
        *,
        shape: cq.Shape,
        label: str,
        code_prefix: str,
        profile: ManufacturingProfile,
    ) -> ManufacturingCheck:
        if not shape.isValid():
            return ManufacturingCheck(
                code=f"{code_prefix}_INVALID",
                label=f"{label} region",
                status=CheckStatus.ERROR,
                message=f"{label} region contains invalid geometry.",
            )

        solids = tuple(shape.Solids())

        if not solids:
            return ManufacturingCheck(
                code=f"{code_prefix}_NO_SOLID",
                label=f"{label} region",
                status=CheckStatus.ERROR,
                message=f"{label} region contains no printable solid.",
            )

        volumes = [
            float(solid.Volume())
            for solid in solids
        ]

        minimum_volume = min(volumes)

        if minimum_volume < profile.min_color_region_volume:
            return ManufacturingCheck(
                code=f"{code_prefix}_REGION_SMALL",
                label=f"{label} region",
                status=CheckStatus.WARNING,
                message=(
                    f"{label} contains one or more very small printable "
                    "volumes."
                ),
                measured_value=minimum_volume,
                required_value=profile.min_color_region_volume,
                unit="mm^3",
            )

        return ManufacturingCheck(
            code=f"{code_prefix}_REGION_OK",
            label=f"{label} region",
            status=CheckStatus.OK,
            message=(
                f"{label} region is valid and contains printable volume."
            ),
            measured_value=minimum_volume,
            required_value=profile.min_color_region_volume,
            unit="mm^3",
        )
