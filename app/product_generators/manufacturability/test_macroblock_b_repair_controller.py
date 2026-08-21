from __future__ import annotations

from .consolidated_validator import ManufacturingValidator, ValidationStatus
from .contract import RULES
from .repair_controller import (
    BoundedManufacturingRepairController,
    RepairCandidate,
)


def _validate(state: dict[str, bool]):
    statuses = {rule.code: ValidationStatus.OK for rule in RULES}

    if not state["wall_ok"]:
        statuses["STRUCTURAL_WALL_THICKNESS"] = ValidationStatus.ERROR

    if not state["text_ok"]:
        statuses["TEXT_DEPTH"] = ValidationStatus.WARNING

    if not state["cad_ok"]:
        statuses["CAD_VALID"] = ValidationStatus.ERROR

    statuses["CLEARANCE"] = ValidationStatus.SOURCE_PENDING

    return ManufacturingValidator().from_status_map(statuses)


def main() -> None:
    initial = {
        "wall_ok": False,
        "text_ok": False,
        "cad_ok": True,
    }

    controller = BoundedManufacturingRepairController[dict[str, bool]](
        max_attempts=6
    )

    candidates = (
        RepairCandidate(
            rule_code="CLEARANCE",
            label="must-not-run-without-source",
            apply=lambda state: {**state, "pending_touched": True},
        ),
        RepairCandidate(
            rule_code="STRUCTURAL_WALL_THICKNESS",
            label="increase-wall-thickness",
            apply=lambda state: {**state, "wall_ok": True},
        ),
        RepairCandidate(
            rule_code="TEXT_DEPTH",
            label="unsafe-text-repair",
            apply=lambda state: {**state, "text_ok": True, "cad_ok": False},
        ),
    )

    result = controller.repair(
        state=initial,
        validate=_validate,
        candidates=candidates,
    )

    if result.state.get("pending_touched"):
        raise RuntimeError("SOURCE_PENDING rule incorrectly triggered repair.")
    if not result.state["wall_ok"]:
        raise RuntimeError("Blocking wall repair was not accepted.")
    if result.state["text_ok"]:
        raise RuntimeError("Regressive warning repair was incorrectly accepted.")
    if result.report.blocking_errors:
        raise RuntimeError("Accepted repair did not clear blocking errors.")
    if result.report.count(ValidationStatus.SOURCE_PENDING) != 1:
        raise RuntimeError("SOURCE_PENDING status was not preserved.")
    if len(result.attempts) != 2:
        raise RuntimeError(f"Expected 2 actual repair attempts, got {len(result.attempts)}.")

    wall_attempt, warning_attempt = result.attempts
    if not wall_attempt.accepted:
        raise RuntimeError("Safe blocking repair should have been accepted.")
    if warning_attempt.accepted:
        raise RuntimeError("Repair introducing a blocking regression must be rejected.")

    print("DOBO Macroblock B - Bounded Manufacturing Repair")
    print("24-rule full revalidation", True, "OK")
    print("SOURCE_PENDING ignored", True, "OK")
    print("blocking repair accepted", True, "OK")
    print("regressive repair rejected", True, "OK")
    print("Macroblock B Repair Controller: Valid OK")


if __name__ == "__main__":
    main()
