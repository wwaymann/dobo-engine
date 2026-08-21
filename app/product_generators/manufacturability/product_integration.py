from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from product_generators.surface_designer.composition_spec import (
    ProductCompositionParser,
)
from product_generators.surface_designer.multicolor_product import (
    build_multicolor_product,
)
from product_generators.surface_designer.three_mf_exporter import (
    ThreeMFExporter,
    ThreeMFRegion,
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
from .final_geometry import FinalGeometryManufacturingAnalyzer
from .final_product_validation import FinalProductAnalyzer
from .product_profile import ProductManufacturingProfile
from .production_orientation import ProductionOrientationPlanner
from .production_validation import ProductionAnalyzer
from .profile import ManufacturingProfile
from .report import CheckStatus
from .source import build_structural_body_source
from .stability import BaseStabilityAnalyzer
from .structural import StructuralBodyValidator
from .text_geometry import PrintedTextFeatureAnalyzer
from .text_validation import TextDepthAnalyzer, TextRegionVolumeAnalyzer
from .three_mf_project_inspector import ThreeMFProjectInspector


@dataclass(frozen=True, slots=True)
class RealProductValidationResult:
    report: ConsolidatedManufacturingReport
    three_mf_path: str
    final_volume: float
    production_orientation: str


def _status_from_check(status: CheckStatus) -> ValidationStatus:
    if status is CheckStatus.OK:
        return ValidationStatus.OK
    if status is CheckStatus.WARNING:
        return ValidationStatus.WARNING
    if status is CheckStatus.ERROR:
        return ValidationStatus.ERROR
    if status is CheckStatus.NOT_AVAILABLE:
        return ValidationStatus.NOT_AVAILABLE
    raise RuntimeError(f"Unsupported structural check status: {status}")


def _exported_placement_is_on_bed(
    *,
    bounds: tuple[float, float, float, float, float, float] | None,
    profile: ManufacturingProfile,
) -> bool:
    """Validate the real exported 3MF bounds against the production bed.

    The exporter uses machine coordinates with the K1 Max bed spanning
    X/Y=0..max_size and Z=0 at the build plate. A small existing bed tolerance
    is allowed only at the numerical boundary; no threshold is weakened.
    """
    if bounds is None:
        return False
    xmin, xmax, ymin, ymax, zmin, _zmax = bounds
    tolerance = max(profile.bed_z_tolerance, profile.layer_height)
    return bool(
        xmin >= -tolerance
        and ymin >= -tolerance
        and xmax <= profile.max_size_x + tolerance
        and ymax <= profile.max_size_y + tolerance
        and abs(zmin) <= tolerance
    )


def _export_planned_orientation(
    *,
    product,
    orientation_label: str,
) -> None:
    """Propagate one planner decision to every physical material region.

    Rotation is applied in shared CAD space. Bed translation is deliberately
    left to ThreeMFExporter, which computes one common transform for the whole
    compound product. This prevents Body/Text/Decoration from being dropped to
    the plate independently and preserves the validated multicolor partition.
    """
    rotated_regions = tuple(
        ThreeMFRegion(
            name=region.name,
            shape=ProductionOrientationPlanner.rotate_shape(
                region.shape,
                orientation_label,
            ),
            color=region.color,
            filament_slot=region.filament_slot,
        )
        for region in product.export_regions
    )
    ThreeMFExporter().export(
        regions=rotated_regions,
        path=product.three_mf_path,
    )


def validate_real_multicolor_product(
    specification_path: str | Path,
    *,
    profile: ManufacturingProfile | None = None,
    product_profile: ProductManufacturingProfile | None = None,
) -> RealProductValidationResult:
    """Build the real multicolor product and validate the full 24-rule contract.

    Final-product geometric rules are derived from the actual final printable
    B-Rep/tessellation. The deterministic production planner chooses a bounded
    real orientation from the same geometry, and that exact rotation is then
    propagated to all 3MF material regions before the exported project is
    inspected. No product-specific fixture values are used.
    """
    manufacturing_profile = profile if profile is not None else ManufacturingProfile()
    product_rules = product_profile if product_profile is not None else ProductManufacturingProfile()
    manufacturing_profile.validate()
    product_rules.validate()

    specification = ProductCompositionParser().parse_file(specification_path)
    product = build_multicolor_product(specification_path)
    structural_source = build_structural_body_source(specification_path)
    statuses: dict[str, ValidationStatus] = {}

    # Select production orientation before orientation-dependent checks and
    # propagate the exact shared rotation into the real exported 3MF.
    orientation_plan = ProductionOrientationPlanner().plan(
        shape=product.final_shape,
        profile=manufacturing_profile,
    )
    production_shape = orientation_plan.selected.shape
    production_orientation = orientation_plan.selected.label
    _export_planned_orientation(
        product=product,
        orientation_label=production_orientation,
    )

    # Final product
    final = FinalProductAnalyzer().analyze(shape=product.final_shape)
    statuses["CAD_VALID"] = ValidationStatus.OK if final.cad_valid else ValidationStatus.ERROR
    statuses["CONNECTED_FINAL_PRODUCT"] = ValidationStatus.OK if final.connected else ValidationStatus.ERROR
    statuses["NO_DEGENERATE_GEOMETRY"] = ValidationStatus.OK if final.degenerate_geometry_ok else ValidationStatus.ERROR

    final_geometry = FinalGeometryManufacturingAnalyzer()
    clearance = final_geometry.clearance(
        shape=product.final_shape,
        minimum_required=manufacturing_profile.min_clearance,
    )
    statuses["CLEARANCE"] = (
        ValidationStatus.OK
        if clearance.available and clearance.valid
        else ValidationStatus.WARNING
    )

    # OVERHANG is orientation-dependent. Validate the same orientation that is
    # now physically written into the production 3MF, not the design-space pose.
    overhang = final_geometry.overhang(
        shape=production_shape,
        maximum_allowed_angle=manufacturing_profile.max_overhang_angle,
        bed_tolerance=max(
            manufacturing_profile.bed_z_tolerance,
            manufacturing_profile.layer_height,
        ),
    )
    statuses["OVERHANG"] = (
        ValidationStatus.OK
        if overhang.available and overhang.valid
        else ValidationStatus.WARNING
    )

    # Structural body
    structural_report = StructuralBodyValidator().validate(
        source=structural_source,
        manufacturing_profile=manufacturing_profile,
        product_profile=product_rules,
    )
    for check in structural_report.checks:
        statuses[check.code] = _status_from_check(check.status)

    stability = BaseStabilityAnalyzer().analyze(shape=structural_source.structural_body)
    statuses["BASE_CONTACT_AREA"] = (
        ValidationStatus.OK
        if stability.support_area >= manufacturing_profile.min_bed_contact_area
        else ValidationStatus.WARNING
    )

    # Text
    text_feature = PrintedTextFeatureAnalyzer().analyze(
        text_region=product.text_region,
        minimum_required=manufacturing_profile.min_text_stroke,
    )
    statuses["TEXT_PRINTABLE_STROKE"] = (
        ValidationStatus.OK
        if text_feature.available and text_feature.printable
        else ValidationStatus.WARNING
    )

    text_depth = specification.text.depth if specification.text is not None else None
    depth = TextDepthAnalyzer().analyze(
        depth=text_depth,
        minimum_required=manufacturing_profile.min_text_depth,
    )
    statuses["TEXT_DEPTH"] = (
        ValidationStatus.OK if depth.available and depth.valid else ValidationStatus.WARNING
    )

    text_volume = TextRegionVolumeAnalyzer().analyze(
        text_region=product.text_region,
        minimum_required=manufacturing_profile.min_text_region_volume,
    )
    statuses["TEXT_REGION_VOLUME"] = (
        ValidationStatus.OK
        if text_volume.available and text_volume.valid
        else ValidationStatus.WARNING
    )

    # Decoration
    decoration_size = DecorationFeatureSizeAnalyzer().analyze(
        decoration_geometry=product.decoration_region,
        minimum_required=manufacturing_profile.min_decoration_feature_size,
    )
    statuses["DECORATION_FEATURE_SIZE"] = (
        ValidationStatus.OK
        if decoration_size.available and decoration_size.printable
        else ValidationStatus.WARNING
    )

    decoration_volume = DecorationRegionVolumeAnalyzer().analyze(
        decoration_region=product.decoration_region,
        minimum_required=manufacturing_profile.min_decoration_region_volume,
    )
    statuses["DECORATION_REGION_VOLUME"] = (
        ValidationStatus.OK
        if decoration_volume.available and decoration_volume.valid
        else ValidationStatus.WARNING
    )

    # Color partition
    color = ColorRegionAnalyzer().analyze(
        final_shape=product.final_shape,
        regions={
            "Body": product.body_region,
            "Text": product.text_region,
            "Decoration": product.decoration_region,
        },
        minimum_region_volume=manufacturing_profile.min_color_region_volume,
        volume_tolerance=max(1.0, float(product.final_shape.Volume()) * 2.0e-4),
    )
    color_mapping = {
        "COLOR_REGIONS_VALID": color.regions_valid,
        "COLOR_REGION_MIN_VOLUME": color.minimum_volume_ok,
        "COLOR_REGION_CONNECTIVITY": color.connectivity_ok,
        "COLOR_INTERFACE_INTEGRITY": color.interface_integrity_ok,
    }
    for code, valid in color_mapping.items():
        statuses[code] = (
            ValidationStatus.OK
            if valid
            else ValidationStatus.ERROR
            if code in {"COLOR_REGIONS_VALID", "COLOR_INTERFACE_INTEGRITY"}
            else ValidationStatus.WARNING
        )

    # Production validates the same planned orientation that was exported.
    production = ProductionAnalyzer()
    size = production.physical_size(
        shape=production_shape,
        max_x=manufacturing_profile.max_size_x,
        max_y=manufacturing_profile.max_size_y,
        max_z=manufacturing_profile.max_size_z,
    )
    statuses["PHYSICAL_SIZE_LIMITS"] = ValidationStatus.OK if size.valid else ValidationStatus.ERROR

    project = ThreeMFProjectInspector().inspect(product.three_mf_path)
    statuses["ORIENTATION_ON_BED"] = (
        ValidationStatus.OK
        if project.build_item_count == 1
        and _exported_placement_is_on_bed(
            bounds=project.transformed_bounds,
            profile=manufacturing_profile,
        )
        else ValidationStatus.ERROR
    )
    statuses["MULTICOLOR_3MF_INTEGRITY"] = (
        ValidationStatus.OK if project.valid else ValidationStatus.ERROR
    )

    filament = production.filament_assignment(
        assigned_slots=project.filament_slots,
        expected_region_count=3,
    )
    statuses["FILAMENT_ASSIGNMENT"] = (
        ValidationStatus.OK if filament.valid else ValidationStatus.ERROR
    )

    report = ManufacturingValidator().from_status_map(statuses)
    return RealProductValidationResult(
        report=report,
        three_mf_path=product.three_mf_path,
        final_volume=float(product.final_shape.Volume()),
        production_orientation=production_orientation,
    )
