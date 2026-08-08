from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True, slots=True)
class PhysicalSizeResult:
    valid: bool
    size_x: float
    size_y: float
    size_z: float


@dataclass(frozen=True, slots=True)
class OrientationResult:
    valid: bool
    z_min: float


@dataclass(frozen=True, slots=True)
class FilamentAssignmentResult:
    available: bool
    valid: bool | None
    assigned_slots: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MulticolorIntegrityResult:
    available: bool
    valid: bool | None
    top_level_build_items: int | None
    component_count: int | None


class ProductionAnalyzer:
    """
    Production-level checks independent of slicer-specific UI.

    Implemented:
      PHYSICAL_SIZE_LIMITS
      ORIENTATION_ON_BED

    Creality-specific project integrity and filament assignment are validated
    from explicit exporter metadata when supplied.
    """

    def physical_size(
        self,
        *,
        shape: cq.Shape,
        max_x: float,
        max_y: float,
        max_z: float,
    ) -> PhysicalSizeResult:
        box = shape.BoundingBox()

        sx = float(box.xlen)
        sy = float(box.ylen)
        sz = float(box.zlen)

        return PhysicalSizeResult(
            valid=(
                sx <= max_x
                and sy <= max_y
                and sz <= max_z
            ),
            size_x=sx,
            size_y=sy,
            size_z=sz,
        )

    def orientation_on_bed(
        self,
        *,
        shape: cq.Shape,
        tolerance: float,
    ) -> OrientationResult:
        z_min = float(
            shape.BoundingBox().zmin
        )

        return OrientationResult(
            valid=abs(z_min) <= tolerance,
            z_min=z_min,
        )

    def filament_assignment(
        self,
        *,
        assigned_slots: tuple[int, ...] | None,
        expected_region_count: int,
    ) -> FilamentAssignmentResult:
        if assigned_slots is None:
            return FilamentAssignmentResult(
                available=False,
                valid=None,
                assigned_slots=(),
            )

        valid = bool(
            len(assigned_slots) == expected_region_count
            and all(slot > 0 for slot in assigned_slots)
            and len(set(assigned_slots)) == expected_region_count
        )

        return FilamentAssignmentResult(
            available=True,
            valid=valid,
            assigned_slots=assigned_slots,
        )

    def multicolor_3mf_integrity(
        self,
        *,
        top_level_build_items: int | None,
        component_count: int | None,
        expected_component_count: int,
    ) -> MulticolorIntegrityResult:
        if (
            top_level_build_items is None
            or component_count is None
        ):
            return MulticolorIntegrityResult(
                available=False,
                valid=None,
                top_level_build_items=None,
                component_count=None,
            )

        valid = bool(
            top_level_build_items == 1
            and component_count == expected_component_count
        )

        return MulticolorIntegrityResult(
            available=True,
            valid=valid,
            top_level_build_items=top_level_build_items,
            component_count=component_count,
        )
