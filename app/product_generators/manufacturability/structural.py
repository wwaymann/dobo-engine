from __future__ import annotations

from dataclasses import dataclass

from .cavity import (
    ClosedCavityAnalyzer,
    DrainageAnalyzer,
    InternalVolumeAnalyzer,
)
from .local_thickness import LocalThicknessAnalyzer
from .product_profile import ProductManufacturingProfile
from .profile import ManufacturingProfile
from .report import (
    CheckStatus,
    ManufacturingCheck,
)
from .source import StructuralBodySource
from .stability import BaseStabilityAnalyzer


@dataclass(frozen=True, slots=True)
class StructuralValidationReport:
    checks: tuple[ManufacturingCheck, ...]

    @property
    def blocking_errors(self) -> tuple[ManufacturingCheck, ...]:
        return tuple(
            check
            for check in self.checks
            if check.status is CheckStatus.ERROR
        )


class StructuralBodyValidator:
    def validate(
        self,
        *,
        source: StructuralBodySource,
        manufacturing_profile: ManufacturingProfile,
        product_profile: ProductManufacturingProfile,
    ) -> StructuralValidationReport:
        manufacturing_profile.validate()
        product_profile.validate()

        body = source.structural_body

        thickness = LocalThicknessAnalyzer().analyze(
            shape=body,
            threshold=manufacturing_profile.min_wall_thickness,
            samples_per_axis=3,
        )

        checks: list[ManufacturingCheck] = []

        if thickness.minimum is None:
            checks.append(
                ManufacturingCheck(
                    code="STRUCTURAL_WALL_THICKNESS",
                    label="Structural wall thickness",
                    status=CheckStatus.ERROR,
                    message=(
                        "Structural wall thickness produced no usable samples."
                    ),
                )
            )
        elif thickness.minimum < manufacturing_profile.min_wall_thickness:
            checks.append(
                ManufacturingCheck(
                    code="STRUCTURAL_WALL_THICKNESS",
                    label="Structural wall thickness",
                    status=CheckStatus.ERROR,
                    message=(
                        f"{thickness.thin_sample_count} of "
                        f"{thickness.sample_count} structural samples "
                        "are below the minimum wall thickness."
                    ),
                    measured_value=thickness.minimum,
                    required_value=manufacturing_profile.min_wall_thickness,
                    unit="mm",
                )
            )
        else:
            checks.append(
                ManufacturingCheck(
                    code="STRUCTURAL_WALL_THICKNESS",
                    label="Structural wall thickness",
                    status=CheckStatus.OK,
                    message=(
                        f"{thickness.sample_count} structural samples pass."
                    ),
                    measured_value=thickness.minimum,
                    required_value=manufacturing_profile.min_wall_thickness,
                    unit="mm",
                )
            )

        stability = BaseStabilityAnalyzer().analyze(
            shape=body
        )

        if not stability.stable:
            checks.append(
                ManufacturingCheck(
                    code="BASE_STABILITY",
                    label="Base stability",
                    status=CheckStatus.ERROR,
                    message=(
                        "Projected center of mass falls outside the "
                        "support polygon."
                    ),
                    measured_value=(
                        stability.margin
                    ),
                    required_value=manufacturing_profile.min_stability_margin,
                    unit="mm",
                )
            )
        elif (
            stability.margin is not None
            and stability.margin
            < manufacturing_profile.min_stability_margin
        ):
            checks.append(
                ManufacturingCheck(
                    code="BASE_STABILITY",
                    label="Base stability",
                    status=CheckStatus.WARNING,
                    message=(
                        "Center of mass is inside the support polygon but "
                        "with a small stability margin."
                    ),
                    measured_value=stability.margin,
                    required_value=manufacturing_profile.min_stability_margin,
                    unit="mm",
                )
            )
        else:
            checks.append(
                ManufacturingCheck(
                    code="BASE_STABILITY",
                    label="Base stability",
                    status=CheckStatus.OK,
                    message=(
                        "Center of mass is inside the support polygon."
                    ),
                    measured_value=stability.margin,
                    required_value=manufacturing_profile.min_stability_margin,
                    unit="mm",
                )
            )

        volume = InternalVolumeAnalyzer().analyze(
            source.internal_cavity
        )

        if not volume.available:
            checks.append(
                ManufacturingCheck(
                    code="INTERNAL_VOLUME",
                    label="Internal usable volume",
                    status=CheckStatus.NOT_AVAILABLE,
                    message=(
                        "Structural source does not yet expose an explicit "
                        "internal cavity solid. No guessed value was used."
                    ),
                )
            )
        elif (
            not volume.valid
            or volume.volume is None
            or volume.volume < product_profile.min_internal_volume
        ):
            checks.append(
                ManufacturingCheck(
                    code="INTERNAL_VOLUME",
                    label="Internal usable volume",
                    status=CheckStatus.ERROR,
                    message="Internal cavity volume is below requirement.",
                    measured_value=volume.volume,
                    required_value=product_profile.min_internal_volume,
                    unit="mm^3",
                )
            )
        else:
            checks.append(
                ManufacturingCheck(
                    code="INTERNAL_VOLUME",
                    label="Internal usable volume",
                    status=CheckStatus.OK,
                    message="Internal cavity volume is sufficient.",
                    measured_value=volume.volume,
                    required_value=product_profile.min_internal_volume,
                    unit="mm^3",
                )
            )

        drainage = DrainageAnalyzer().analyze(
            structural_body=body,
            internal_cavity=source.internal_cavity,
            drainage_tools=source.drainage_tools,
        )

        if not drainage.available:
            checks.append(
                ManufacturingCheck(
                    code="DRAINAGE_PATH",
                    label="Drainage path",
                    status=CheckStatus.NOT_AVAILABLE,
                    message=(
                        "Structural source does not yet expose cavity and "
                        "drainage-tool semantics. No topology guess was used."
                    ),
                )
            )
        elif (
            drainage.path_count is None
            or drainage.path_count
            < product_profile.required_drainage_count
        ):
            checks.append(
                ManufacturingCheck(
                    code="DRAINAGE_PATH",
                    label="Drainage path",
                    status=CheckStatus.ERROR,
                    message="Insufficient connected drainage paths.",
                    measured_value=(
                        float(drainage.path_count or 0)
                    ),
                    required_value=float(
                        product_profile.required_drainage_count
                    ),
                )
            )
        else:
            checks.append(
                ManufacturingCheck(
                    code="DRAINAGE_PATH",
                    label="Drainage path",
                    status=CheckStatus.OK,
                    message="Required drainage paths are connected.",
                    measured_value=float(drainage.path_count),
                    required_value=float(
                        product_profile.required_drainage_count
                    ),
                )
            )

        cavities = ClosedCavityAnalyzer().analyze(
            internal_cavity=source.internal_cavity,
            declared_closed_cavities=(
                source.declared_closed_cavities
            ),
        )

        if not cavities.available:
            checks.append(
                ManufacturingCheck(
                    code="NO_UNINTENDED_CLOSED_CAVITIES",
                    label="Closed cavities",
                    status=CheckStatus.NOT_AVAILABLE,
                    message=(
                        "No explicit cavity/envelope source is available; "
                        "undeclared voids are not guessed from the final B-Rep."
                    ),
                )
            )
        elif (
            cavities.undeclared_count
            and not product_profile.allow_closed_cavities
        ):
            checks.append(
                ManufacturingCheck(
                    code="NO_UNINTENDED_CLOSED_CAVITIES",
                    label="Closed cavities",
                    status=CheckStatus.WARNING,
                    message="Undeclared closed cavities were detected.",
                    measured_value=float(cavities.undeclared_count),
                    required_value=0.0,
                )
            )
        else:
            checks.append(
                ManufacturingCheck(
                    code="NO_UNINTENDED_CLOSED_CAVITIES",
                    label="Closed cavities",
                    status=CheckStatus.OK,
                    message="No undeclared closed cavities detected.",
                    measured_value=0.0,
                    required_value=0.0,
                )
            )

        return StructuralValidationReport(
            checks=tuple(checks)
        )
