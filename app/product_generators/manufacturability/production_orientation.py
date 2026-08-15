from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from .final_geometry import FinalGeometryManufacturingAnalyzer
from .production_validation import ProductionAnalyzer
from .profile import ManufacturingProfile


@dataclass(frozen=True, slots=True)
class ProductionOrientationCandidate:
    label: str
    shape: cq.Shape
    size_valid: bool
    overhang_valid: bool
    overhang_angle: float
    size_x: float
    size_y: float
    size_z: float
    footprint_area: float

    @property
    def production_valid(self) -> bool:
        return self.size_valid and self.overhang_valid

    @property
    def ranking_key(self) -> tuple[float, ...]:
        # Valid manufacturing orientations always win. Among valid candidates,
        # prefer lower unsupported overhang, lower build height, and then a
        # larger XY footprint. Labels provide deterministic final tie-breaking.
        return (
            0.0 if self.production_valid else 1.0,
            0.0 if self.size_valid else 1.0,
            0.0 if self.overhang_valid else 1.0,
            float(self.overhang_angle),
            float(self.size_z),
            -float(self.footprint_area),
        )


@dataclass(frozen=True, slots=True)
class ProductionOrientationPlan:
    selected: ProductionOrientationCandidate
    candidates: tuple[ProductionOrientationCandidate, ...]


class ProductionOrientationPlanner:
    """Choose a bounded deterministic build orientation from real geometry.

    The planner does not alter manufacturing thresholds and does not claim to
    replace slicer simulation. It evaluates a small, explicit orientation set
    using the same physical-size and overhang analyzers used by the 24-rule
    manufacturing contract. Every returned shape is translated onto Z=0.
    """

    _ROTATIONS = (
        ("current", None, 0.0),
        ("rotate-x-90", (1.0, 0.0, 0.0), 90.0),
        ("rotate-x-minus-90", (1.0, 0.0, 0.0), -90.0),
        ("rotate-y-90", (0.0, 1.0, 0.0), 90.0),
        ("rotate-y-minus-90", (0.0, 1.0, 0.0), -90.0),
    )

    def __init__(self) -> None:
        self._production = ProductionAnalyzer()
        self._geometry = FinalGeometryManufacturingAnalyzer()

    @staticmethod
    def _place_on_bed(shape: cq.Shape) -> cq.Shape:
        z_min = float(shape.BoundingBox().zmin)
        return shape.translate(cq.Vector(0.0, 0.0, -z_min))

    def _oriented_shape(
        self,
        shape: cq.Shape,
        axis: tuple[float, float, float] | None,
        angle: float,
    ) -> cq.Shape:
        if axis is None:
            oriented = shape
        else:
            oriented = shape.rotate(
                cq.Vector(0.0, 0.0, 0.0),
                cq.Vector(*axis),
                float(angle),
            )
        return self._place_on_bed(oriented)

    def plan(
        self,
        *,
        shape: cq.Shape,
        profile: ManufacturingProfile | None = None,
    ) -> ProductionOrientationPlan:
        manufacturing = profile or ManufacturingProfile()
        manufacturing.validate()

        candidates: list[ProductionOrientationCandidate] = []
        for label, axis, angle in self._ROTATIONS:
            oriented = self._oriented_shape(shape, axis, angle)
            size = self._production.physical_size(
                shape=oriented,
                max_x=manufacturing.max_size_x,
                max_y=manufacturing.max_size_y,
                max_z=manufacturing.max_size_z,
            )
            overhang = self._geometry.overhang(
                shape=oriented,
                maximum_allowed_angle=manufacturing.max_overhang_angle,
                bed_tolerance=manufacturing.bed_z_tolerance,
            )
            angle_value = (
                float(overhang.maximum_overhang_angle)
                if overhang.maximum_overhang_angle is not None
                else 90.0
            )
            candidates.append(
                ProductionOrientationCandidate(
                    label=label,
                    shape=oriented,
                    size_valid=bool(size.valid),
                    overhang_valid=bool(overhang.valid),
                    overhang_angle=angle_value,
                    size_x=float(size.size_x),
                    size_y=float(size.size_y),
                    size_z=float(size.size_z),
                    footprint_area=float(size.size_x * size.size_y),
                )
            )

        if not candidates:
            raise RuntimeError("No production orientation candidates generated")

        selected = min(
            enumerate(candidates),
            key=lambda item: (item[1].ranking_key, item[0]),
        )[1]
        return ProductionOrientationPlan(
            selected=selected,
            candidates=tuple(candidates),
        )
