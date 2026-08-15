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
    replace slicer simulation. It evaluates a finite, explicit orientation set
    using the same physical-size and overhang analyzers used by the 24-rule
    manufacturing contract. Every candidate used for ranking is translated
    onto Z=0, while ``rotate_shape`` exposes the exact shared rotation so the
    same decision can be propagated to every material region before export.

    Orthogonal poses are complemented by 30/45/60-degree X/Y poses. The denser
    bounded set is still deterministic and general-purpose, but can resolve
    geometries where one diagonal angle is too shallow for an embossed feature
    and another is too steep for the vessel wall. Manufacturing thresholds are
    never changed to make an orientation pass.
    """

    _ROTATIONS = (
        ("current", None, 0.0),
        ("rotate-x-30", (1.0, 0.0, 0.0), 30.0),
        ("rotate-x-minus-30", (1.0, 0.0, 0.0), -30.0),
        ("rotate-y-30", (0.0, 1.0, 0.0), 30.0),
        ("rotate-y-minus-30", (0.0, 1.0, 0.0), -30.0),
        ("rotate-x-45", (1.0, 0.0, 0.0), 45.0),
        ("rotate-x-minus-45", (1.0, 0.0, 0.0), -45.0),
        ("rotate-y-45", (0.0, 1.0, 0.0), 45.0),
        ("rotate-y-minus-45", (0.0, 1.0, 0.0), -45.0),
        ("rotate-x-60", (1.0, 0.0, 0.0), 60.0),
        ("rotate-x-minus-60", (1.0, 0.0, 0.0), -60.0),
        ("rotate-y-60", (0.0, 1.0, 0.0), 60.0),
        ("rotate-y-minus-60", (0.0, 1.0, 0.0), -60.0),
        ("rotate-x-90", (1.0, 0.0, 0.0), 90.0),
        ("rotate-x-minus-90", (1.0, 0.0, 0.0), -90.0),
        ("rotate-y-90", (0.0, 1.0, 0.0), 90.0),
        ("rotate-y-minus-90", (0.0, 1.0, 0.0), -90.0),
    )

    def __init__(self) -> None:
        self._production = ProductionAnalyzer()
        self._geometry = FinalGeometryManufacturingAnalyzer()

    @classmethod
    def _rotation_by_label(
        cls,
        label: str,
    ) -> tuple[tuple[float, float, float] | None, float]:
        for candidate_label, axis, angle in cls._ROTATIONS:
            if candidate_label == label:
                return axis, float(angle)
        raise ValueError(f"Unknown production orientation: {label!r}")

    @classmethod
    def rotate_shape(
        cls,
        shape: cq.Shape,
        label: str,
    ) -> cq.Shape:
        """Apply only the selected rotation, preserving shared CAD alignment.

        Bed placement must be applied once to the complete multiregion product,
        never independently to Body/Text/Decoration. The 3MF exporter therefore
        receives these rotated regions and computes one shared bed transform.
        """
        axis, angle = cls._rotation_by_label(label)
        if axis is None:
            return shape
        return shape.rotate(
            cq.Vector(0.0, 0.0, 0.0),
            cq.Vector(*axis),
            angle,
        )

    @staticmethod
    def _place_on_bed(shape: cq.Shape) -> cq.Shape:
        z_min = float(shape.BoundingBox().zmin)
        return shape.translate(cq.Vector(0.0, 0.0, -z_min))

    @classmethod
    def _oriented_shape(
        cls,
        shape: cq.Shape,
        label: str,
    ) -> cq.Shape:
        return cls._place_on_bed(cls.rotate_shape(shape, label))

    def plan(
        self,
        *,
        shape: cq.Shape,
        profile: ManufacturingProfile | None = None,
    ) -> ProductionOrientationPlan:
        manufacturing = profile or ManufacturingProfile()
        manufacturing.validate()

        candidates: list[ProductionOrientationCandidate] = []
        for label, _axis, _angle in self._ROTATIONS:
            oriented = self._oriented_shape(shape, label)
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
