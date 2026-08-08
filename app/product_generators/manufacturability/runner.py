from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from product_generators.surface_designer.multicolor_product import (
    build_multicolor_product,
)

from .analyzer import ManufacturabilityAnalyzer
from .profile import ManufacturingProfile
from .report import ManufacturingReport
from .semantic import SemanticManufacturingAnalyzer


@dataclass(frozen=True, slots=True)
class ManufacturingRunResult:
    report: ManufacturingReport
    source_3mf: str
    source_step: str


def analyze_phase_6_product(
    *,
    specification_path: str | Path,
    profile: ManufacturingProfile | None = None,
) -> ManufacturingRunResult:
    product = build_multicolor_product(
        specification_path
    )

    active_profile = (
        profile
        if profile is not None
        else ManufacturingProfile()
    )

    generic = ManufacturabilityAnalyzer().analyze(
        shape=product.final_shape,
        profile=active_profile,
        color_regions=(
            product.body_region,
            product.text_region,
            product.decoration_region,
        ),
    )

    semantic = SemanticManufacturingAnalyzer().analyze(
        body_region=product.body_region,
        text_region=product.text_region,
        decoration_region=product.decoration_region,
        profile=active_profile,
    )

    # Replace the generic whole-product local thickness interpretation
    # with semantic checks for Body/Text/Decoration.
    generic_checks = tuple(
        check
        for check in generic.checks
        if check.code not in {
            "LOCAL_THICKNESS_OK",
            "LOCAL_THICKNESS_LOW",
            "LOCAL_THICKNESS_INSUFFICIENT_SAMPLES",
        }
    )

    report = ManufacturingReport(
        checks=(
            *generic_checks,
            semantic.body_check,
            semantic.text_check,
            semantic.decoration_check,
        )
    )

    return ManufacturingRunResult(
        report=report,
        source_3mf=product.three_mf_path,
        source_step=product.step_path,
    )
