from __future__ import annotations

from pathlib import Path

from .consolidated_validator import (
    ValidationStatus,
)
from .product_integration import (
    validate_real_multicolor_product,
)


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "phase_5_product_spec.json"
)


def main() -> None:
    result = (
        validate_real_multicolor_product(
            SPEC_PATH
        )
    )

    report = result.report

    print(
        "DOBO Manufacturability - Phase 7.10"
    )
    print(
        "Real Product End-to-End Validation"
    )
    print(
        "-----------------------------------"
    )

    for item in report.results:
        print(
            f"{item.code:<34} "
            f"{item.status.value}"
        )

    print(
        "-----------------------------------"
    )

    print(
        "OK",
        report.count(
            ValidationStatus.OK
        ),
    )

    print(
        "WARNING",
        report.count(
            ValidationStatus.WARNING
        ),
    )

    print(
        "ERROR",
        report.count(
            ValidationStatus.ERROR
        ),
    )

    print(
        "SOURCE_PENDING",
        report.count(
            ValidationStatus.SOURCE_PENDING
        ),
    )

    print(
        "NOT_AVAILABLE",
        report.count(
            ValidationStatus.NOT_AVAILABLE
        ),
    )

    print(
        "blocking errors",
        len(
            report.blocking_errors
        ),
    )

    print(
        "final volume",
        f"{result.final_volume:.3f}",
        "mm^3",
    )

    print(
        "3MF",
        result.three_mf_path,
    )

    expected_pending = {
        "CLEARANCE",
        "OVERHANG",
    }

    actual_pending = {
        item.code
        for item in report.results
        if item.status
        is ValidationStatus.SOURCE_PENDING
    }

    if actual_pending != expected_pending:
        raise RuntimeError(
            "Unexpected SOURCE_PENDING rules: "
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
        if item.status
        is ValidationStatus.NOT_AVAILABLE
    }

    if (
        actual_not_available
        != expected_not_available
    ):
        raise RuntimeError(
            "Unexpected NOT_AVAILABLE rules: "
            f"{sorted(actual_not_available)}"
        )

    text_stroke = next(
        item
        for item in report.results
        if item.code == "TEXT_PRINTABLE_STROKE"
    )
    if text_stroke.status is not ValidationStatus.OK:
        raise RuntimeError(
            "Real final text material geometry did not satisfy printable stroke."
        )

    if report.blocking_errors:
        raise RuntimeError(
            "Real product has blocking manufacturing errors: "
            f"{[item.code for item in report.blocking_errors]}"
        )

    if report.count(
        ValidationStatus.WARNING
    ):
        raise RuntimeError(
            "Real product produced unexpected manufacturing warnings."
        )

    if report.count(
        ValidationStatus.ERROR
    ):
        raise RuntimeError(
            "Real product produced manufacturing errors."
        )

    if report.count(
        ValidationStatus.OK
    ) != 19:
        raise RuntimeError(
            "Expected 19 real-product OK rules after text-source integration."
        )

    print(
        "-----------------------------------"
    )

    print(
        "Phase 7.10 Real Product Integration: Valid OK"
    )


if __name__ == "__main__":
    main()
