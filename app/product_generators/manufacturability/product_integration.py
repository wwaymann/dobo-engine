from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from product_generators.surface_designer.composition_spec import (
    ProductCompositionParser,
)
from product_generators.surface_designer.multicolor_product import (
    build_multicolor_product,
)

from .color_validation import ColorRegionAnalyzer
from .consolidated_validator import (
    ConsolidatedManufacturingReport,
    ManufacturingValidator,
    ValidationStatus,
)
from .decoration_validation import (
    DecorationFeatureSizeAnalyzer,
    DecorationRegionVolumeAnalyzer,
)
from .final_product_validation import (
    FinalProductAnalyzer,
)
from .product_profile import (
    ProductManufacturingProfile,
)
from .production_validation import (
    ProductionAnalyzer,
)
from .profile import ManufacturingProfile
from .report import CheckStatus
from .source import (
    build_structural_body_source,
)
from .stability import BaseStabilityAnalyzer
from .structural import StructuralBodyValidator
from .text_geometry import PrintedTextFeatureAnalyzer
from .text_validation import (
    TextDepthAnalyzer,
    TextRegionVolumeAnalyzer,
)
from .three_mf_project_inspector import (
    ThreeMFProjectInspector,
)


@dataclass(frozen=True, slots=True)
class RealProductValidationResult:
    report: ConsolidatedManufacturingReport
    three_mf_path: str
    final_volume: float


def _status_from_check(
    status: CheckStatus,
) -> ValidationStatus:
    if status is CheckStatus.OK:
        return ValidationStatus.OK

    if status is CheckStatus.WARNING:
        return ValidationStatus.WARNING

    if status is CheckStatus.ERROR:
        return ValidationStatus.ERROR

    if status is CheckStatus.NOT_AVAILABLE:
        return ValidationStatus.NOT_AVAILABLE

    raise RuntimeError(
        f"Unsupported structural check status: {status}"
    )


def validate_real_multicolor_product(
    specification_path: str | Path,
    *,
    profile: ManufacturingProfile | None = None,
    product_profile: ProductManufacturingProfile | None = None,
) -> RealProductValidationResult:
    """
    Build the real Phase-6.5 multicolor product and feed every currently
    exposed manufacturing source into the consolidated 24-rule contract.

    No geometry is guessed.

    Expected unresolved rules for the current hybrid stress product:
      SOURCE_PENDING:
        CLEARANCE
        OVERHANG

      NOT_AVAILABLE:
        INTERNAL_VOLUME
        DRAINAGE_PATH
        NO_UNINTENDED_CLOSED_CAVITIES
    """

    manufacturing_profile = (
        profile
        if profile is not None
        else ManufacturingProfile()
    )

    product_rules = (
        product_profile
        if product_profile is not None
        else ProductManufacturingProfile()
    )

    manufacturing_profile.validate()
    product_rules.validate()

    specification = (
        ProductCompositionParser()
        .parse_file(
            specification_path
        )
    )

    product = build_multicolor_product(
        specification_path
    )

    structural_source = (
        build_structural_body_source(
            specification_path
        )
    )

    statuses: dict[
        str,
        ValidationStatus,
    ] = {}

    # ---------------------------------------------------------
    # Final product
    # ---------------------------------------------------------
    final = FinalProductAnalyzer().analyze(
        shape=product.final_shape
    )

    statuses["CAD_VALID"] = (
        ValidationStatus.OK
        if final.cad_valid
        else ValidationStatus.ERROR
    )

    statuses[
        "CONNECTED_FINAL_PRODUCT"
    ] = (
        ValidationStatus.OK
        if final.connected
        else ValidationStatus.ERROR
    )

    statuses[
        "NO_DEGENERATE_GEOMETRY"
    ] = (
        ValidationStatus.OK
        if final.degenerate_geometry_ok
        else ValidationStatus.ERROR
    )

    statuses["CLEARANCE"] = (
        ValidationStatus.SOURCE_PENDING
    )

    statuses["OVERHANG"] = (
        ValidationStatus.SOURCE_PENDING
    )

    # ---------------------------------------------------------
    # Structural body
    # ---------------------------------------------------------
    structural_report = (
        StructuralBodyValidator()
        .validate(
            source=structural_source,
            manufacturing_profile=(
                manufacturing_profile
            ),
            product_profile=product_rules,
        )
    )

    for check in structural_report.checks:
        statuses[
            check.code
        ] = _status_from_check(
            check.status
        )

    # BASE_CONTACT_AREA is derived from the same validated
    # section-footprint used by BaseStabilityAnalyzer.
    stability = (
        BaseStabilityAnalyzer()
        .analyze(
            shape=(
                structural_source
                .structural_body
            )
        )
    )

    statuses[
        "BASE_CONTACT_AREA"
    ] = (
        ValidationStatus.OK
        if stability.support_area
        >= manufacturing_profile.min_bed_contact_area
        else ValidationStatus.WARNING
    )

    # ---------------------------------------------------------
    # Text
    # ---------------------------------------------------------
    # Validate the actual post-mapping, post-boolean material geometry that
    # will be exported to 3MF. This closes the former SOURCE_PENDING state
    # without reconstructing or guessing the planar font source.
    text_feature = (
        PrintedTextFeatureAnalyzer()
        .analyze(
            text_region=product.text_region,
            minimum_required=(
                manufacturing_profile
                .min_text_stroke
            ),
        )
    )

    statuses[
        "TEXT_PRINTABLE_STROKE"
    ] = (
        ValidationStatus.OK
        if text_feature.available
        and text_feature.printable
        else ValidationStatus.WARNING
    )

    text_depth = (
        specification.text.depth
        if specification.text is not None
        else None
    )

    depth = (
        TextDepthAnalyzer()
        .analyze(
            depth=text_depth,
            minimum_required=(
                manufacturing_profile
                .min_text_depth
            ),
        )
    )

    statuses["TEXT_DEPTH"] = (
        ValidationStatus.OK
        if depth.available
        and depth.valid
        else ValidationStatus.WARNING
    )

    text_volume = (
        TextRegionVolumeAnalyzer()
        .analyze(
            text_region=(
                product.text_region
            ),
            minimum_required=(
                manufacturing_profile
                .min_text_region_volume
            ),
        )
    )

    statuses[
        "TEXT_REGION_VOLUME"
    ] = (
        ValidationStatus.OK
        if text_volume.available
        and text_volume.valid
        else ValidationStatus.WARNING
    )

    # ---------------------------------------------------------
    # Decoration
    # ---------------------------------------------------------
    # Use the actual printable decoration material region.
    # This is stricter and more production-relevant than using
    # the pre-intersection stud tool.
    decoration_size = (
        DecorationFeatureSizeAnalyzer()
        .analyze(
            decoration_geometry=(
                product.decoration_region
            ),
            minimum_required=(
                manufacturing_profile
                .min_decoration_feature_size
            ),
        )
    )

    statuses[
        "DECORATION_FEATURE_SIZE"
    ] = (
        ValidationStatus.OK
        if decoration_size.available
        and decoration_size.printable
        else ValidationStatus.WARNING
    )

    decoration_volume = (
        DecorationRegionVolumeAnalyzer()
        .analyze(
            decoration_region=(
                product.decoration_region
            ),
            minimum_required=(
                manufacturing_profile
                .min_decoration_region_volume
            ),
        )
    )

    statuses[
        "DECORATION_REGION_VOLUME"
    ] = (
        ValidationStatus.OK
        if decoration_volume.available
        and decoration_volume.valid
        else ValidationStatus.WARNING
    )

    # ---------------------------------------------------------
    # Color partition
    # ---------------------------------------------------------
    color = (
        ColorRegionAnalyzer()
        .analyze(
            final_shape=(
                product.final_shape
            ),
            regions={
                "Body": (
                    product.body_region
                ),
                "Text": (
                    product.text_region
                ),
                "Decoration": (
                    product.decoration_region
                ),
            },
            minimum_region_volume=(
                manufacturing_profile
                .min_color_region_volume
            ),
            # Phase 6 already validated conservation
            # using a product-scaled tolerance.
            volume_tolerance=max(
                1.0,
                float(
                    product.final_shape
                    .Volume()
                )
                * 2.0e-4,
            ),
        )
    )

    color_mapping = {
        "COLOR_REGIONS_VALID": (
            color.regions_valid
        ),
        "COLOR_REGION_MIN_VOLUME": (
            color.minimum_volume_ok
        ),
        "COLOR_REGION_CONNECTIVITY": (
            color.connectivity_ok
        ),
        "COLOR_INTERFACE_INTEGRITY": (
            color.interface_integrity_ok
        ),
    }

    for code, valid in color_mapping.items():
        statuses[code] = (
            ValidationStatus.OK
            if valid
            else ValidationStatus.ERROR
            if code
            in {
                "COLOR_REGIONS_VALID",
                "COLOR_INTERFACE_INTEGRITY",
            }
            else ValidationStatus.WARNING
        )

    # ---------------------------------------------------------
    # Production
    # ---------------------------------------------------------
    production = ProductionAnalyzer()

    size = production.physical_size(
        shape=product.final_shape,
        max_x=manufacturing_profile.max_size_x,
        max_y=manufacturing_profile.max_size_y,
        max_z=manufacturing_profile.max_size_z,
    )

    statuses[
        "PHYSICAL_SIZE_LIMITS"
    ] = (
        ValidationStatus.OK
        if size.valid
        else ValidationStatus.ERROR
    )

    # CAD coordinates are not required to be bed-centered before
    # the Creality exporter. The exporter is the validated source
    # of final print orientation/placement.
    project = (
        ThreeMFProjectInspector()
        .inspect(
            product.three_mf_path
        )
    )

    statuses[
        "ORIENTATION_ON_BED"
    ] = (
        ValidationStatus.OK
        if project.build_item_count == 1
        else ValidationStatus.ERROR
    )

    statuses[
        "MULTICOLOR_3MF_INTEGRITY"
    ] = (
        ValidationStatus.OK
        if project.valid
        else ValidationStatus.ERROR
    )

    filament = (
        production
        .filament_assignment(
            assigned_slots=(
                project.filament_slots
            ),
            expected_region_count=3,
        )
    )

    statuses[
        "FILAMENT_ASSIGNMENT"
    ] = (
        ValidationStatus.OK
        if filament.valid
        else ValidationStatus.ERROR
    )

    report = (
        ManufacturingValidator()
        .from_status_map(
            statuses
        )
    )

    return RealProductValidationResult(
        report=report,
        three_mf_path=(
            product.three_mf_path
        ),
        final_volume=float(
            product.final_shape.Volume()
        ),
    )
