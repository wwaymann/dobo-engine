from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

import cadquery as cq

from product_generators.surface_designer.three_mf_exporter import ThreeMFRegion

from .product_integration import _export_planned_orientation
from .production_orientation import ProductionOrientationPlanner
from .profile import ManufacturingProfile
from .three_mf_project_inspector import ThreeMFProjectInspector


@dataclass(frozen=True, slots=True)
class _ExportFixture:
    export_regions: tuple[ThreeMFRegion, ...]
    three_mf_path: str


def _size_from_bounds(
    bounds: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float]:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    return (
        xmax - xmin,
        ymax - ymin,
        zmax - zmin,
    )


def main() -> None:
    # Three touching material regions form one 10 x 20 x 30 mm product.
    # The planner is free to select any of its bounded orientations; this test
    # verifies that the exact selected orientation reaches the exported 3MF.
    body = cq.Workplane("XY").box(4.0, 20.0, 30.0, centered=(False, False, False)).val()
    text = (
        cq.Workplane("XY")
        .box(3.0, 20.0, 30.0, centered=(False, False, False))
        .translate((4.0, 0.0, 0.0))
        .val()
    )
    decoration = (
        cq.Workplane("XY")
        .box(3.0, 20.0, 30.0, centered=(False, False, False))
        .translate((7.0, 0.0, 0.0))
        .val()
    )
    final_shape = body.fuse(text).fuse(decoration).clean()

    profile = ManufacturingProfile()
    plan = ProductionOrientationPlanner().plan(
        shape=final_shape,
        profile=profile,
    )

    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "planned_orientation.3mf")
        fixture = _ExportFixture(
            export_regions=(
                ThreeMFRegion("Body", body, "#EAEAEA", 1),
                ThreeMFRegion("Text", text, "#6D3BFF", 2),
                ThreeMFRegion("Decoration", decoration, "#19A974", 3),
            ),
            three_mf_path=path,
        )
        _export_planned_orientation(
            product=fixture,
            orientation_label=plan.selected.label,
        )

        inspection = ThreeMFProjectInspector().inspect(path)
        if not inspection.valid:
            raise RuntimeError("Planned-orientation 3MF is structurally invalid")
        if inspection.transformed_bounds is None:
            raise RuntimeError("Planned-orientation 3MF has no transformed bounds")

        exported_size = _size_from_bounds(inspection.transformed_bounds)
        planned_size = (
            plan.selected.size_x,
            plan.selected.size_y,
            plan.selected.size_z,
        )
        for actual, expected in zip(exported_size, planned_size):
            if abs(actual - expected) > 0.15:
                raise RuntimeError(
                    "Exported 3MF does not match selected planner orientation: "
                    f"actual={exported_size} expected={planned_size} "
                    f"orientation={plan.selected.label}"
                )

        zmin = inspection.transformed_bounds[4]
        if abs(zmin) > max(profile.bed_z_tolerance, profile.layer_height):
            raise RuntimeError(
                f"Planned 3MF is not on bed: zmin={zmin}"
            )

        print("DOBO Macroblock B - Planned Orientation -> 3MF")
        print("orientation", plan.selected.label)
        print("planned size", tuple(round(value, 3) for value in planned_size))
        print("exported size", tuple(round(value, 3) for value in exported_size))
        print("build items", inspection.build_item_count)
        print("filament slots", inspection.filament_slots)
        print("Macroblock B Planned 3MF Export: Valid OK")


if __name__ == "__main__":
    main()
