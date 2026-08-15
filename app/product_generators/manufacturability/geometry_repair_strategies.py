from __future__ import annotations

from collections.abc import Iterable

import cadquery as cq

from .production_orientation import ProductionOrientationPlanner
from .repair_controller import RepairCandidate


def _place_on_bed(shape: cq.Shape) -> cq.Shape:
    z_min = float(shape.BoundingBox().zmin)
    return shape.translate(cq.Vector(0.0, 0.0, -z_min))


def build_orientation_repair_candidates() -> tuple[RepairCandidate[cq.Shape], ...]:
    """Deterministic candidate orientations for a real overhang warning.

    The repair space is intentionally identical to the planner's finite search,
    excluding the unchanged ``current`` pose. No manufacturing threshold is
    modified. A candidate is accepted only after the bounded repair controller
    performs complete 24-rule revalidation and proves that the target warning
    is resolved without introducing a blocking regression.
    """

    candidates: list[RepairCandidate[cq.Shape]] = []
    for label, _steps in ProductionOrientationPlanner.rotation_specs():
        if label == "current":
            continue

        def apply(
            shape: cq.Shape,
            *,
            label: str = label,
        ) -> cq.Shape:
            rotated = ProductionOrientationPlanner.rotate_shape(shape, label)
            return _place_on_bed(rotated)

        candidates.append(
            RepairCandidate(
                rule_code="OVERHANG",
                label=label,
                apply=apply,
            )
        )

    return tuple(candidates)


def clearance_translation_candidate(
    *,
    solid_index: int,
    vector: tuple[float, float, float],
    label: str | None = None,
) -> RepairCandidate[cq.Shape]:
    """Move one disconnected printable component by an explicit safe vector.

    This is intentionally parameterized rather than guessed. A caller derives
    the vector from product semantics or an assembly constraint, then the
    bounded controller accepts the change only after complete revalidation.
    """

    if solid_index < 0:
        raise ValueError("solid_index must be non-negative")
    if not any(abs(float(value)) > 1.0e-12 for value in vector):
        raise ValueError("clearance repair vector must be non-zero")

    def apply(shape: cq.Shape) -> cq.Shape:
        solids = list(shape.Solids())
        if solid_index >= len(solids):
            raise IndexError("solid_index is outside the final solid list")
        solids[solid_index] = solids[solid_index].translate(cq.Vector(*vector))
        return cq.Compound.makeCompound(solids)

    return RepairCandidate(
        rule_code="CLEARANCE",
        label=label or f"translate-solid-{solid_index}",
        apply=apply,
    )


def chain_geometry_candidates(
    *candidate_groups: Iterable[RepairCandidate[cq.Shape]],
) -> tuple[RepairCandidate[cq.Shape], ...]:
    return tuple(candidate for group in candidate_groups for candidate in group)
