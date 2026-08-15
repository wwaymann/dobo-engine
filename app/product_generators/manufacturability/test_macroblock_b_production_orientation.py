from __future__ import annotations

import cadquery as cq

from .production_orientation import ProductionOrientationPlanner
from .profile import ManufacturingProfile


def main() -> None:
    planner = ProductionOrientationPlanner()

    shape = cq.Workplane("XY").box(10.0, 20.0, 30.0, centered=(True, True, False)).val()
    plan = planner.plan(shape=shape)

    if len(plan.candidates) != 29:
        raise RuntimeError(f"Expected 29 bounded orientations, got {len(plan.candidates)}")
    if not plan.selected.production_valid:
        raise RuntimeError("Selected orientation must satisfy size and overhang gates")
    if abs(float(plan.selected.shape.BoundingBox().zmin)) > 1.0e-6:
        raise RuntimeError("Selected orientation is not placed on the print bed")
    if plan.selected.size_z > 10.0 + 1.0e-6:
        raise RuntimeError(
            f"Expected minimum build height near 10 mm, got {plan.selected.size_z:.6f}"
        )

    labels = {candidate.label for candidate in plan.candidates}
    for required in {
        "rotate-x-30",
        "rotate-x-minus-30",
        "rotate-y-30",
        "rotate-y-minus-30",
        "rotate-x-45",
        "rotate-x-minus-45",
        "rotate-y-45",
        "rotate-y-minus-45",
        "rotate-x-60",
        "rotate-x-minus-60",
        "rotate-y-60",
        "rotate-y-minus-60",
        "rotate-x-30-y-30",
        "rotate-x-30-y-minus-30",
        "rotate-x-minus-30-y-30",
        "rotate-x-minus-30-y-minus-30",
        "rotate-x-45-y-45",
        "rotate-x-45-y-minus-45",
        "rotate-x-minus-45-y-45",
        "rotate-x-minus-45-y-minus-45",
        "rotate-x-60-y-30",
        "rotate-x-60-y-minus-30",
        "rotate-x-minus-60-y-30",
        "rotate-x-minus-60-y-minus-30",
    }:
        if required not in labels:
            raise RuntimeError(f"Missing bounded orientation {required}")

    constrained = ManufacturingProfile(max_size_x=15.0, max_size_y=35.0, max_size_z=25.0)
    constrained_plan = planner.plan(shape=shape, profile=constrained)
    if not constrained_plan.selected.production_valid:
        raise RuntimeError("Planner failed to find an existing valid axis permutation")
    if constrained_plan.selected.size_x > constrained.max_size_x + 1.0e-6:
        raise RuntimeError("Selected orientation exceeds X machine limit")
    if constrained_plan.selected.size_y > constrained.max_size_y + 1.0e-6:
        raise RuntimeError("Selected orientation exceeds Y machine limit")
    if constrained_plan.selected.size_z > constrained.max_size_z + 1.0e-6:
        raise RuntimeError("Selected orientation exceeds Z machine limit")

    print("DOBO Macroblock B - Advanced Production Orientation")
    print("candidate count", len(plan.candidates))
    print("selected", plan.selected.label)
    print(
        "selected size",
        f"{plan.selected.size_x:.3f}",
        f"{plan.selected.size_y:.3f}",
        f"{plan.selected.size_z:.3f}",
    )
    print("selected overhang", f"{plan.selected.overhang_angle:.3f}")
    print("constrained selected", constrained_plan.selected.label)
    print("Macroblock B Production Orientation: Valid OK")


if __name__ == "__main__":
    main()
