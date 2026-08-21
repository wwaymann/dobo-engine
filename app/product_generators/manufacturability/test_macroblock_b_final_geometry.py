from __future__ import annotations

import cadquery as cq

from .final_geometry import FinalGeometryManufacturingAnalyzer


def main() -> None:
    analyzer = FinalGeometryManufacturingAnalyzer()

    single = cq.Workplane("XY").box(10.0, 10.0, 10.0, centered=(True, True, False)).val()
    clearance_single = analyzer.clearance(shape=single, minimum_required=0.25)
    if not clearance_single.available or not clearance_single.valid:
        raise RuntimeError("Single connected solid must satisfy inter-solid clearance.")

    first = cq.Workplane("XY").box(4.0, 4.0, 4.0, centered=(True, True, False)).val()
    second = (
        cq.Workplane("XY")
        .transformed(offset=(4.10, 0.0, 0.0))
        .box(4.0, 4.0, 4.0, centered=(True, True, False))
        .val()
    )
    close_pair = cq.Compound.makeCompound([first, second])
    clearance_close = analyzer.clearance(shape=close_pair, minimum_required=0.25)
    if clearance_close.valid:
        raise RuntimeError("0.10 mm disconnected-solid clearance must fail a 0.25 mm rule.")

    box_overhang = analyzer.overhang(
        shape=single,
        maximum_allowed_angle=50.0,
        bed_tolerance=0.20,
    )
    if not box_overhang.available or not box_overhang.valid:
        raise RuntimeError("Bed-supported box must not create a false overhang warning.")

    column = cq.Workplane("XY").box(4.0, 4.0, 10.0, centered=(True, True, False)).val()
    slab = (
        cq.Workplane("XY")
        .workplane(offset=10.0)
        .box(12.0, 4.0, 2.0, centered=(True, True, False))
        .val()
    )
    cantilever = column.fuse(slab)
    cantilever_overhang = analyzer.overhang(
        shape=cantilever,
        maximum_allowed_angle=50.0,
        bed_tolerance=0.20,
    )
    if cantilever_overhang.valid:
        raise RuntimeError("Horizontal unsupported cantilever must trigger overhang warning.")
    if (cantilever_overhang.maximum_overhang_angle or 0.0) < 80.0:
        raise RuntimeError("Cantilever overhang angle was not measured from real geometry.")

    print("DOBO Macroblock B - Real Final Geometry")
    print("single clearance", clearance_single.valid)
    print("close-pair clearance", clearance_close.minimum_clearance, clearance_close.valid)
    print("box overhang", box_overhang.maximum_overhang_angle, box_overhang.valid)
    print("cantilever overhang", cantilever_overhang.maximum_overhang_angle, cantilever_overhang.valid)
    print("Macroblock B Final Geometry: Valid OK")


if __name__ == "__main__":
    main()
