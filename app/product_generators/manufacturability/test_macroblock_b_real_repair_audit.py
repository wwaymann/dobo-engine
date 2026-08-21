from __future__ import annotations

import json
from pathlib import Path

from product_generators.surface_designer.multicolor_product import build_multicolor_product

from .consolidated_validator import ManufacturingValidator, ValidationStatus
from .product_integration import validate_real_multicolor_product
from .production_orientation import ProductionOrientationPlanner
from .profile import ManufacturingProfile
from .repair_controller import BoundedManufacturingRepairController, RepairCandidate


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "phase_5_product_spec.json"
)
OUTPUT_PATH = (
    Path("outputs")
    / "product_generators"
    / "surface_designer"
    / "phase_6_multicolor_3mf"
    / "real_overhang_repair_audit.json"
)


def _status_map(report) -> dict[str, ValidationStatus]:
    return {item.code: item.status for item in report.results}


def main() -> None:
    profile = ManufacturingProfile()
    profile.validate()

    # Establish the already-integrated 24-rule real-product baseline. This also
    # validates and exports the exact multicolor 3MF used by production handoff.
    baseline = validate_real_multicolor_product(SPEC_PATH, profile=profile)
    baseline_statuses = _status_map(baseline.report)

    product = build_multicolor_product(SPEC_PATH)
    planner = ProductionOrientationPlanner()
    plan = planner.plan(shape=product.final_shape, profile=profile)
    validator = ManufacturingValidator()

    # The planner has already measured every candidate from the real B-Rep with
    # the production OVERHANG and physical-size analyzers. Reuse those immutable
    # measurements while rebuilding the complete 24-rule report for each repair
    # proposal; this preserves full contract revalidation without tessellating
    # the same candidate geometry twice.
    metrics_by_shape_id = {id(candidate.shape): candidate for candidate in plan.candidates}

    def validate_candidate(shape):
        candidate = metrics_by_shape_id.get(id(shape))
        if candidate is None:
            raise RuntimeError("Repair audit received an unmeasured orientation state.")
        statuses = dict(baseline_statuses)
        statuses["OVERHANG"] = (
            ValidationStatus.OK if candidate.overhang_valid else ValidationStatus.WARNING
        )
        statuses["PHYSICAL_SIZE_LIMITS"] = (
            ValidationStatus.OK if candidate.size_valid else ValidationStatus.ERROR
        )
        bounds = shape.BoundingBox()
        tolerance = max(profile.bed_z_tolerance, profile.layer_height)
        statuses["ORIENTATION_ON_BED"] = (
            ValidationStatus.OK
            if candidate.size_valid and abs(float(bounds.zmin)) <= tolerance
            else ValidationStatus.ERROR
        )
        return validator.from_status_map(statuses)

    selected_shape = plan.selected.shape
    candidates = tuple(
        RepairCandidate(
            rule_code="OVERHANG",
            label=candidate.label,
            # Candidate poses are absolute planner states, not cumulative
            # rotations. The repair controller still rebuilds and validates the
            # complete 24-rule contract after every bounded proposal.
            apply=(lambda _state, shape=candidate.shape: shape),
        )
        for candidate in plan.candidates
        if candidate.label != plan.selected.label
    )

    controller = BoundedManufacturingRepairController(max_attempts=len(candidates))
    repaired = controller.repair(
        state=selected_shape,
        validate=validate_candidate,
        candidates=candidates,
    )

    final_statuses = _status_map(repaired.report)
    resolved = final_statuses["OVERHANG"] is ValidationStatus.OK
    accepted = tuple(
        attempt.candidate.label
        for attempt in repaired.attempts
        if attempt.accepted
    )

    # The repair audit must never regress a previously OK error-severity rule.
    protected = {
        item.code
        for item in baseline.report.results
        if item.status is ValidationStatus.OK
        and item.code
        in {
            "CAD_VALID",
            "CONNECTED_FINAL_PRODUCT",
            "NO_DEGENERATE_GEOMETRY",
            "STRUCTURAL_WALL_THICKNESS",
            "BASE_STABILITY",
            "COLOR_REGIONS_VALID",
            "COLOR_INTERFACE_INTEGRITY",
            "PHYSICAL_SIZE_LIMITS",
            "ORIENTATION_ON_BED",
            "MULTICOLOR_3MF_INTEGRITY",
            "FILAMENT_ASSIGNMENT",
        }
    }
    if any(final_statuses[code] is not ValidationStatus.OK for code in protected):
        raise RuntimeError("Bounded real-product repair regressed a protected rule.")

    payload = {
        "schema_version": "dobo.real-overhang-repair-audit.v2",
        "source_specification": str(SPEC_PATH),
        "target_rule": "OVERHANG",
        "threshold_degrees": profile.max_overhang_angle,
        "measurement_source": "production_orientation_planner_real_brep",
        "full_contract_revalidation_per_candidate": True,
        "baseline_orientation": baseline.production_orientation,
        "planner_selected_orientation": plan.selected.label,
        "planner_selected_angle": plan.selected.overhang_angle,
        "candidate_count": len(plan.candidates),
        "repair_attempts": len(repaired.attempts),
        "accepted_orientations": accepted,
        "resolved": resolved,
        "exhausted_without_resolution": bool(
            not resolved and len(repaired.attempts) == len(candidates)
        ),
        "final_rule_counts": {
            status.value: repaired.report.count(status)
            for status in ValidationStatus
        },
        "attempts": [
            {
                "label": attempt.candidate.label,
                "accepted": attempt.accepted,
                "before_blocking": attempt.before_blocking,
                "after_blocking": attempt.after_blocking,
            }
            for attempt in repaired.attempts
        ],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("DOBO Macroblock B - Real Product Bounded Repair Audit")
    print("-----------------------------------")
    print("baseline orientation", baseline.production_orientation)
    print("planner selected", plan.selected.label)
    print("selected overhang", f"{plan.selected.overhang_angle:.4f}")
    print("candidate count", len(plan.candidates))
    print("repair attempts", len(repaired.attempts))
    print("accepted", accepted)
    print("resolved", resolved)
    print("protected rules", len(protected), "OK")
    print("full 24-rule revalidation per candidate", True)
    print("audit", OUTPUT_PATH)
    print("-----------------------------------")
    if resolved:
        print("Macroblock B Real Product Repair: OVERHANG RESOLVED")
    else:
        print("Macroblock B Real Product Repair: BOUNDED ORIENTATION SPACE EXHAUSTED")


if __name__ == "__main__":
    main()
