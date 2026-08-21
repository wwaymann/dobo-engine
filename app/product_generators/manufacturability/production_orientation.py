from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from .final_geometry import FinalGeometryManufacturingAnalyzer
from .production_validation import ProductionAnalyzer
from .profile import ManufacturingProfile


RotationStep = tuple[tuple[float, float, float], float]
RotationSpec = tuple[str, tuple[RotationStep, ...]]


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

    Candidate poses are shared by the production planner and the bounded repair
    controller.  The set is finite, deterministic and product-agnostic.  It
    samples single-axis poses plus diagonal build directions that cannot be
    represented by one X/Y rotation alone.  Manufacturing thresholds are never
    altered; every pose is measured by the same real tessellated OVERHANG and
    physical-size analyzers used by the 24-rule contract.
    """

    @staticmethod
    def _single_axis_rotations() -> tuple[RotationSpec, ...]:
        items: list[RotationSpec] = []
        for axis_name, axis in (("x", (1.0, 0.0, 0.0)), ("y", (0.0, 1.0, 0.0))):
            for magnitude in (15, 30, 45, 60, 75, 90):
                for sign, suffix in ((1, ""), (-1, "minus-")):
                    angle = float(sign * magnitude)
                    label = f"rotate-{axis_name}-{suffix}{magnitude}"
                    items.append((label, ((axis, angle),)))
        return tuple(items)

    @staticmethod
    def _compound_rotations() -> tuple[RotationSpec, ...]:
        # Same-magnitude diagonals plus a small number of asymmetric diagonal
        # directions.  This expands directional coverage without an unbounded
        # optimiser and keeps CI cost predictable.
        pairs = (
            (15, 15),
            (30, 30),
            (45, 45),
            (60, 60),
            (75, 75),
            (60, 30),
            (75, 30),
            (75, 45),
        )
        items: list[RotationSpec] = []
        for x_mag, y_mag in pairs:
            for x_sign in (1, -1):
                for y_sign in (1, -1):
                    x_suffix = "" if x_sign > 0 else "minus-"
                    y_suffix = "" if y_sign > 0 else "minus-"
                    label = (
                        f"rotate-x-{x_suffix}{x_mag}-"
                        f"y-{y_suffix}{y_mag}"
                    )
                    items.append(
                        (
                            label,
                            (
                                ((1.0, 0.0, 0.0), float(x_sign * x_mag)),
                                ((0.0, 1.0, 0.0), float(y_sign * y_mag)),
                            ),
                        )
                    )
        return tuple(items)

    _ROTATIONS: tuple[RotationSpec, ...] = (
        ("current", ()),
        *_single_axis_rotations.__func__(),
        *_compound_rotations.__func__(),
    )

    def __init__(self) -> None:
        self._production = ProductionAnalyzer()
        self._geometry = FinalGeometryManufacturingAnalyzer()

    @classmethod
    def rotation_specs(cls) -> tuple[RotationSpec, ...]:
        return cls._ROTATIONS

    @classmethod
    def _steps_by_label(cls, label: str) -> tuple[RotationStep, ...]:
        for candidate_label, steps in cls._ROTATIONS:
            if candidate_label == label:
                return steps
        raise ValueError(f"Unknown production orientation: {label!r}")

    @classmethod
    def rotate_shape(cls, shape: cq.Shape, label: str) -> cq.Shape:
        rotated = shape
        origin = cq.Vector(0.0, 0.0, 0.0)
        for axis, angle in cls._steps_by_label(label):
            rotated = rotated.rotate(origin, cq.Vector(*axis), angle)
        return rotated

    @staticmethod
    def _place_on_bed(shape: cq.Shape) -> cq.Shape:
        z_min = float(shape.BoundingBox().zmin)
        return shape.translate(cq.Vector(0.0, 0.0, -z_min))

    @classmethod
    def _oriented_shape(cls, shape: cq.Shape, label: str) -> cq.Shape:
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
        for label, _steps in self._ROTATIONS:
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
