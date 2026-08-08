from __future__ import annotations

from .consolidated_validator import (
    ManufacturingValidator,
    ValidationStatus,
)
from .contract import RULES


def main() -> None:
    validator = ManufacturingValidator()

    complete = {
        rule.code: ValidationStatus.OK
        for rule in RULES
    }

    report = validator.from_status_map(complete)

    if len(report.results) != 24:
        raise RuntimeError(
            f"Expected 24 results, got {len(report.results)}."
        )

    if report.blocking_errors:
        raise RuntimeError(
            "24-OK fixture must have zero blocking errors."
        )

    if report.count(ValidationStatus.OK) != 24:
        raise RuntimeError(
            "24-OK fixture did not preserve all statuses."
        )

    current = dict(complete)

    for code in (
        "CLEARANCE",
        "OVERHANG",
        "TEXT_PRINTABLE_STROKE",
        "TEXT_REGION_VOLUME",
        "DECORATION_FEATURE_SIZE",
        "DECORATION_REGION_VOLUME",
    ):
        current[code] = ValidationStatus.SOURCE_PENDING

    for code in (
        "INTERNAL_VOLUME",
        "DRAINAGE_PATH",
        "NO_UNINTENDED_CLOSED_CAVITIES",
    ):
        current[code] = ValidationStatus.NOT_AVAILABLE

    current_report = validator.from_status_map(current)

    if current_report.blocking_errors:
        raise RuntimeError(
            "Pending/not-available fixture should not fabricate ERROR."
        )

    print("DOBO Manufacturability - Phase 7.9")
    print("Consolidated 24-Rule Contract")
    print("-----------------------------------")
    print("rules", len(RULES))
    print("complete fixture OK", report.count(ValidationStatus.OK))
    print(
        "current-state fixture",
        "OK=",
        current_report.count(ValidationStatus.OK),
        "SOURCE_PENDING=",
        current_report.count(ValidationStatus.SOURCE_PENDING),
        "NOT_AVAILABLE=",
        current_report.count(ValidationStatus.NOT_AVAILABLE),
    )
    print("blocking errors", len(current_report.blocking_errors))
    print("-----------------------------------")
    print("Phase 7.9 Consolidated Contract: Valid OK")


if __name__ == "__main__":
    main()
