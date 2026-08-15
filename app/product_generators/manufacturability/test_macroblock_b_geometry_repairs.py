from __future__ import annotations

import cadquery as cq

from .consolidated_validator import ManufacturingValidator, ValidationStatus
from .contract import RULES
from .final_geometry import FinalGeometryManufacturingAnalyzer
from .geometry_repair_strategies import (
    build_orientation_repair_candidates,
    clearance_translation_candidate,
)
from .repair_controller import BoundedManufacturingRepairController


def _clearance_report(shape: cq.Shape):
    statuses = {rule.code: ValidationStatus.OK for rule in RULES}
    result = FinalGeometryManufacturingAnalyzer().clearance(
        shape=shape,
        minimum_required=0.25,
    )
    statuses["CLEARANCE"] = (
        ValidationStatus.OK if result.valid else ValidationStatus.WARNING
    )
    return ManufacturingValidator().from_status_map(statuses)


def main() -> None:
    first = cq.Workplane("XY").box(4.0, 4.0, 4.0, centered=(True, True, False)).val()
    second = (
        cq.Workplane("XY")
        .transformed(offset=(4.10, 0.0, 0.0))
        .box(4.0, 4.0, 4.0, centered=(True, True, False))
        .val()
    )
    state = cq.Compound.makeCompound([first, second])

    before = _clearance_report(state)
    if before.count(ValidationStatus.WARNING) != 1:
        raise RuntimeError("Fixture must begin with one real clearance warning.")

    candidate = clearance_translation_candidate(
        solid_index=1,
        vector=(0.40, 0.0, 0.0),
        label="increase-assembly-clearance",
    )
    controller = BoundedManufacturingRepairController[cq.Shape](max_attempts=4)
    repaired = controller.repair(
        state=state,
        validate=_clearance_report,
        candidates=(candidate,),
    )

    if len(repaired.attempts) != 1 or not repaired.attempts[0].accepted:
        raise RuntimeError("Safe clearance repair was not accepted.")
    if repaired.report.count(ValidationStatus.WARNING):
        raise RuntimeError("Clearance warning survived accepted repair.")
    if repaired.report.blocking_errors:
        raise RuntimeError("Clearance repair introduced a blocking regression.")
    if repaired.report.count(ValidationStatus.OK) != 24:
        raise RuntimeError("Repair did not complete full 24-rule revalidation.")

    orientations = build_orientation_repair_candidates()
    if len(orientations) != 4 or any(item.rule_code != "OVERHANG" for item in orientations):
        raise RuntimeError("Deterministic overhang orientation strategy set is incomplete.")

    print("DOBO Macroblock B - Geometry Repair Strategies")
    print("clearance warning before", before.count(ValidationStatus.WARNING))
    print("repair accepted", repaired.attempts[0].accepted)
    print("full contract OK", repaired.report.count(ValidationStatus.OK))
    print("overhang orientation candidates", len(orientations))
    print("Macroblock B Geometry Repairs: Valid OK")


if __name__ == "__main__":
    main()
