from __future__ import annotations

from pathlib import Path

from .consolidated_validator import ValidationStatus
from .product_integration import validate_real_multicolor_product


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "phase_5_product_spec.json"
)


def main() -> None:
    result = validate_real_multicolor_product(SPEC_PATH)
    report = result.report

    print("DOBO Manufacturability - Phase 7.10")
    print("Real Product End-to-End Validation")
    print("-----------------------------------")
    for item in report.results:
        print(f"{item.code:<34} {item.status.value}")
    print("-----------------------------------")
    for status in ValidationStatus:
        print(status.value, report.count(status))
    print("blocking errors", len(report.blocking_errors))
    print("final volume", f"{result.final_volume:.3f}", "mm^3")
    print("3MF", result.three_mf_path)

    actual_pending = {
        item.code
        for item in report.results
        if item.status is ValidationStatus.SOURCE_PENDING
    }
    if actual_pending:
        raise RuntimeError(
            "Real final-product sources must not remain SOURCE_PENDING: "
            f"{sorted(actual_pending)}"
        )

    expected_not_available = {
        "INTERNAL_VOLUME",
        "DRAINAGE_PATH",
        "NO_UNINTENDED_CLOSED_CAVITIES",
    }
    actual_not_available = {
        item.code
        for item in report.results
        if item.status is ValidationStatus.NOT_AVAILABLE
    }
    if actual_not_available != expected_not_available:
        raise RuntimeError(
            "Unexpected NOT_AVAILABLE rules: "
            f"{sorted(actual_not_available)}"
        )

    by_code = {item.code: item.status for item in report.results}
    for code in ("CLEARANCE", "OVERHANG"):
        if by_code[code] not in {ValidationStatus.OK, ValidationStatus.WARNING}:
            raise RuntimeError(f"{code} is not backed by a real geometry result.")

    if by_code["TEXT_PRINTABLE_STROKE"] is not ValidationStatus.OK:
        raise RuntimeError(
            "Real final text material geometry did not satisfy printable stroke."
        )

    if report.blocking_errors:
        raise RuntimeError(
            "Real product has blocking manufacturing errors: "
            f"{[item.code for item in report.blocking_errors]}"
        )

    if report.count(ValidationStatus.ERROR):
        raise RuntimeError("Real product produced manufacturing errors.")

    resolved = (
        report.count(ValidationStatus.OK)
        + report.count(ValidationStatus.WARNING)
    )
    if resolved != 21:
        raise RuntimeError(
            "Expected all 21 available real-product rules to be resolved."
        )

    print("-----------------------------------")
    print("Phase 7.10 Real Product Integration: Valid OK")


if __name__ == "__main__":
    main()
