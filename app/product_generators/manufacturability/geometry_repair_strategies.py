from __future__ import annotations

from collections.abc import Iterable

import cadquery as cq

from .repair_controller import RepairCandidate


def _place_on_bed(shape: cq.Shape) -> cq.Shape:
    z_min = float(shape.BoundingBox().zmin)
    return shape.translate(cq.Vector(0.0, 0.0, -z_min))


def build_orientation_repair_candidates() -> tuple[RepairCandidate[cq.Shape], ...]:
    """Deterministic candidate orientations for a real overhang warning.

    These candidates never change manufacturing thresholds. The bounded repair
    controller is responsible for accepting one only after a full 24-rule
    revalidation proves that the warning is resolved without introducing a
    blocking regression.
    """

    rotations = (
        ("rotate-x-90", (1.0, 0.0, 0.0), 90.0),
        ("rotate-x-minus-90", (1.0, 0.0, 0.0), -90.0),
        ("rotate-y-90", (0.0, 1.0, 0.0), 90.0),
        ("rotate-y-minus-90", (0.0, 1.0, 0.0), -90.0),
    )

    candidates: list[RepairCandidate[cq.Shape]] = []
    for label, axis, angle in rotations:
        def apply(
            shape: cq.Shape,
            *,
            axis: tuple[float, float, float] = axis,
            angle: float = angle,
        ) -> cq.Shape:
            rotated = shape.rotate(
                cq.Vector(0.0, 0.0, 0.0),
                cq.Vector(*axis),
                angle,
            )
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
