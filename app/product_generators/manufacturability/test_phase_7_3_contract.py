from __future__ import annotations

from .contract import (
    VALIDATION_RULES,
    ValidationDomain,
    ValidationSeverity,
    validation_rules_by_code,
)
from .manifest import (
    DEFAULT_VALIDATION_MANIFEST,
)
from .profile import (
    ManufacturingProfile,
)
from .product_profile import (
    ProductManufacturingProfile,
)


EXPECTED_RULE_COUNT = 24


def main() -> None:
    ManufacturingProfile().validate()
    ProductManufacturingProfile().validate()

    manifest = (
        DEFAULT_VALIDATION_MANIFEST
    )

    if manifest.total != EXPECTED_RULE_COUNT:
        raise RuntimeError(
            "Validation contract rule count changed unexpectedly: "
            f"{manifest.total} != {EXPECTED_RULE_COUNT}"
        )

    by_code = validation_rules_by_code()

    if len(by_code) != manifest.total:
        raise RuntimeError(
            "Validation codes must be unique."
        )

    required_codes = {
        "CAD_VALID",
        "CONNECTED_FINAL_PRODUCT",
        "STRUCTURAL_WALL_THICKNESS",
        "BASE_STABILITY",
        "INTERNAL_VOLUME",
        "DRAINAGE_PATH",
        "TEXT_PRINTABLE_STROKE",
        "TEXT_DEPTH",
        "OVERHANG",
        "COLOR_REGIONS_VALID",
        "COLOR_INTERFACE_INTEGRITY",
        "MULTICOLOR_3MF_INTEGRITY",
        "FILAMENT_ASSIGNMENT",
    }

    missing = (
        required_codes
        - set(
            by_code
        )
    )

    if missing:
        raise RuntimeError(
            "Contract is missing mandatory DOBO rules: "
            f"{sorted(missing)}"
        )

    if (
        by_code[
            "STRUCTURAL_WALL_THICKNESS"
        ].domain
        is not ValidationDomain.STRUCTURAL_BODY
    ):
        raise RuntimeError(
            "Structural wall thickness must apply to structural body."
        )

    if (
        by_code[
            "TEXT_PRINTABLE_STROKE"
        ].domain
        is not ValidationDomain.TEXT
    ):
        raise RuntimeError(
            "Text stroke check must apply to text region."
        )

    if (
        by_code[
            "DECORATION_FEATURE_SIZE"
        ].domain
        is not ValidationDomain.DECORATION
    ):
        raise RuntimeError(
            "Decoration feature check must apply to decoration region."
        )

    print(
        "DOBO Manufacturability - Phase 7.3\n"
        "Complete Manufacturing Validation Contract\n"
        "-----------------------------------"
    )

    print(
        "total rules",
        manifest.total,
    )

    print(
        "implemented",
        manifest.implemented,
    )

    print(
        "partial / source pending",
        manifest.partial,
    )

    print(
        "planned",
        manifest.planned,
    )

    print(
        "-----------------------------------"
    )

    for domain in ValidationDomain:
        rules = manifest.by_domain(
            domain
        )

        print(
            domain.value,
            len(rules),
        )

        for rule in rules:
            print(
                "  ",
                f"{rule.code:<32}",
                f"{rule.severity.value:<8}",
                rule.implementation_status,
            )

    print(
        "-----------------------------------"
    )

    errors = sum(
        1
        for rule in VALIDATION_RULES
        if rule.severity
        is ValidationSeverity.ERROR
    )

    warnings = sum(
        1
        for rule in VALIDATION_RULES
        if rule.severity
        is ValidationSeverity.WARNING
    )

    infos = sum(
        1
        for rule in VALIDATION_RULES
        if rule.severity
        is ValidationSeverity.INFO
    )

    print(
        "severity counts",
        {
            "ERROR": errors,
            "WARNING": warnings,
            "INFO": infos,
        },
    )

    print(
        "Phase 7.3 Validation Contract: Valid OK"
    )


if __name__ == "__main__":
    main()
