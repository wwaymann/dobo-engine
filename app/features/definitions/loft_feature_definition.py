"""
DOBO Features

Loft Feature Definition
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from features.contracts import BooleanMode, FeatureDefinition

Vector3 = tuple[float, float, float]

@dataclass(frozen=True, slots=True)
class LoftFeatureDefinition(FeatureDefinition):
    region_references: tuple[tuple[str, str], ...] = ()
    section_offsets: tuple[Vector3, ...] = ()
    output_id: str = ""
    ruled: bool = False
    mode: BooleanMode = BooleanMode.NEW_BODY
    target_body_id: str | None = None
    merge: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_type(self) -> str:
        return "loft"

    def validate(self) -> None:
        FeatureDefinition.validate(self)
        if not isinstance(self.region_references, tuple) or len(self.region_references) < 2:
            raise ValueError("Loft requires at least two region references.")
        for index, reference in enumerate(self.region_references):
            if not isinstance(reference, tuple) or len(reference) != 2:
                raise TypeError(f"Loft region reference {index} must be a pair.")
            if any(not isinstance(value, str) or not value.strip() for value in reference):
                raise ValueError("Loft region references cannot contain empty IDs.")
        if not isinstance(self.output_id, str) or not self.output_id.strip():
            raise ValueError("Loft output_id cannot be empty.")
        if self.section_offsets:
            if len(self.section_offsets) != len(self.region_references):
                raise ValueError("Loft section_offsets count must match region_references.")
            for index, offset in enumerate(self.section_offsets):
                if not isinstance(offset, tuple) or len(offset) != 3:
                    raise TypeError(f"Loft section offset {index} must be a 3-value tuple.")
                for value in offset:
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise TypeError("Loft section offsets must be numeric.")
        if not isinstance(self.ruled, bool):
            raise TypeError("Loft ruled must be boolean.")
        if not isinstance(self.mode, BooleanMode):
            raise TypeError("Loft mode must be BooleanMode.")
        if self.mode.requires_target_body and (
            self.target_body_id is None or not self.target_body_id.strip()
        ):
            raise ValueError("Boolean Loft requires target_body_id.")
        if not isinstance(self.merge, bool):
            raise TypeError("Loft merge must be boolean.")

    @property
    def resolved_section_offsets(self) -> tuple[Vector3, ...]:
        if self.section_offsets:
            return tuple((float(x), float(y), float(z)) for x, y, z in self.section_offsets)
        return tuple((0.0, 0.0, float(index)) for index in range(len(self.region_references)))
