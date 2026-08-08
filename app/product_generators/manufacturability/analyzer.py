from __future__ import annotations

from collections.abc import Iterable

import cadquery as cq

from .local_thickness import (
    LocalThicknessAnalyzer,
)
from .profile import ManufacturingProfile
from .report import (
    CheckStatus,
    ManufacturingCheck,
    ManufacturingReport,
)


class ManufacturabilityAnalyzer:
    """
    Product-layer manufacturability checks.

    This module evaluates finished CAD geometry.
    It does not alter geometry and does not modify the DOBO Kernel.
    """

    def analyze(
        self,
        *,
        shape: cq.Shape,
        profile: ManufacturingProfile,
        color_regions: Iterable[cq.Shape] = (),
    ) -> ManufacturingReport:
        profile.validate()

        if not shape.isValid():
            return ManufacturingReport(
                checks=(
                    ManufacturingCheck(
                        code="INVALID_GEOMETRY",
                        label="Geometry validity",
                        status=CheckStatus.ERROR,
                        message="The final CAD shape is invalid.",
                    ),
                )
            )

        checks = [
            self._check_connected_solids(
                shape
            ),
            self._check_bounding_box(
                shape
            ),
            self._check_bed_contact(
                shape,
                profile,
            ),
            self._check_local_thickness(
                shape,
                profile,
            ),
            self._check_color_regions(
                color_regions,
                profile,
            ),
        ]

        return ManufacturingReport(
            checks=tuple(
                checks
            )
        )

    @staticmethod
    def _check_connected_solids(
        shape: cq.Shape,
    ) -> ManufacturingCheck:
        solid_count = len(
            shape.Solids()
        )

        if solid_count == 1:
            return ManufacturingCheck(
                code="CONNECTED_SOLID",
                label="Connected solid",
                status=CheckStatus.OK,
                message=(
                    "Final product contains "
                    "one connected solid."
                ),
                measured_value=1.0,
                required_value=1.0,
            )

        return ManufacturingCheck(
            code="DISCONNECTED_SOLIDS",
            label="Connected solid",
            status=CheckStatus.ERROR,
            message=(
                "Final product contains "
                f"{solid_count} disconnected solids."
            ),
            measured_value=float(
                solid_count
            ),
            required_value=1.0,
        )

    @staticmethod
    def _check_bounding_box(
        shape: cq.Shape,
    ) -> ManufacturingCheck:
        box = shape.BoundingBox()

        if (
            box.xlen <= 0.0
            or box.ylen <= 0.0
            or box.zlen <= 0.0
        ):
            return ManufacturingCheck(
                code="INVALID_SIZE",
                label="Overall size",
                status=CheckStatus.ERROR,
                message=(
                    "Product bounding box "
                    "contains a zero dimension."
                ),
            )

        return ManufacturingCheck(
            code="SIZE_VALID",
            label="Overall size",
            status=CheckStatus.OK,
            message=(
                "Product bounding box is valid: "
                f"{box.xlen:.2f} x "
                f"{box.ylen:.2f} x "
                f"{box.zlen:.2f} mm."
            ),
        )

    @staticmethod
    def _check_bed_contact(
        shape: cq.Shape,
        profile: ManufacturingProfile,
    ) -> ManufacturingCheck:
        box = shape.BoundingBox()
        z_min = box.zmin

        tolerance = max(
            profile.layer_height
            * 0.5,
            0.05,
        )

        total_area = 0.0

        for face in shape.Faces():
            center = face.Center()

            if (
                abs(
                    center.z
                    - z_min
                )
                > tolerance
            ):
                continue

            normal = face.normalAt()

            if normal.z > -0.5:
                continue

            total_area += float(
                face.Area()
            )

        if (
            total_area
            >= profile.min_bed_contact_area
        ):
            return ManufacturingCheck(
                code="BED_CONTACT_OK",
                label="Bed contact",
                status=CheckStatus.OK,
                message=(
                    "Bed contact area "
                    "is sufficient."
                ),
                measured_value=(
                    total_area
                ),
                required_value=(
                    profile.min_bed_contact_area
                ),
                unit="mm^2",
            )

        return ManufacturingCheck(
            code="BED_CONTACT_LOW",
            label="Bed contact",
            status=CheckStatus.WARNING,
            message=(
                "Bed contact area is below "
                "the preferred threshold."
            ),
            measured_value=total_area,
            required_value=(
                profile.min_bed_contact_area
            ),
            unit="mm^2",
        )

    @staticmethod
    def _check_local_thickness(
        shape: cq.Shape,
        profile: ManufacturingProfile,
    ) -> ManufacturingCheck:
        result = (
            LocalThicknessAnalyzer()
            .analyze(
                shape=shape,
                threshold=(
                    profile.min_wall_thickness
                ),
                samples_per_axis=3,
            )
        )

        if (
            result.minimum
            is None
            or result.sample_count
            == 0
        ):
            return ManufacturingCheck(
                code="LOCAL_THICKNESS_INSUFFICIENT_SAMPLES",
                label="Local thickness",
                status=CheckStatus.WARNING,
                message=(
                    "Local thickness sampling "
                    "could not produce measurements."
                ),
            )

        if (
            result.minimum
            < profile.min_wall_thickness
        ):
            return ManufacturingCheck(
                code="LOCAL_THICKNESS_LOW",
                label="Local thickness",
                status=CheckStatus.WARNING,
                message=(
                    "Sampling detected local solid "
                    "spans below the preferred "
                    "wall thickness. "
                    f"{result.thin_sample_count} of "
                    f"{result.sample_count} samples "
                    "are below threshold."
                ),
                measured_value=(
                    result.minimum
                ),
                required_value=(
                    profile.min_wall_thickness
                ),
                unit="mm",
            )

        return ManufacturingCheck(
            code="LOCAL_THICKNESS_OK",
            label="Local thickness",
            status=CheckStatus.OK,
            message=(
                "All measured local solid spans "
                "meet the minimum wall thickness. "
                f"{result.sample_count} samples checked."
            ),
            measured_value=(
                result.minimum
            ),
            required_value=(
                profile.min_wall_thickness
            ),
            unit="mm",
        )

    @staticmethod
    def _check_color_regions(
        color_regions: Iterable[cq.Shape],
        profile: ManufacturingProfile,
    ) -> ManufacturingCheck:
        regions = tuple(
            color_regions
        )

        if not regions:
            return ManufacturingCheck(
                code="COLOR_REGIONS_NOT_PROVIDED",
                label="Color regions",
                status=CheckStatus.WARNING,
                message=(
                    "No multicolor regions were "
                    "provided to the analyzer."
                ),
            )

        invalid_regions = []
        volumes = []

        for index, region in enumerate(
            regions,
            start=1,
        ):
            if not region.isValid():
                invalid_regions.append(
                    index
                )
                continue

            volume = float(
                region.Volume()
            )

            volumes.append(
                volume
            )

            if (
                volume
                < profile.min_color_region_volume
            ):
                invalid_regions.append(
                    index
                )

        if invalid_regions:
            return ManufacturingCheck(
                code="COLOR_REGION_TOO_SMALL",
                label="Color regions",
                status=CheckStatus.WARNING,
                message=(
                    "One or more color regions "
                    "are invalid or below the "
                    "minimum region volume: "
                    f"{invalid_regions}."
                ),
                measured_value=(
                    min(
                        volumes
                    )
                    if volumes
                    else 0.0
                ),
                required_value=(
                    profile.min_color_region_volume
                ),
                unit="mm^3",
            )

        return ManufacturingCheck(
            code="COLOR_REGIONS_OK",
            label="Color regions",
            status=CheckStatus.OK,
            message=(
                f"{len(regions)} color regions "
                "are valid and above the "
                "minimum volume."
            ),
            measured_value=min(
                volumes
            ),
            required_value=(
                profile.min_color_region_volume
            ),
            unit="mm^3",
        )
