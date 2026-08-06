"""
DOBO Features

Shell Feature Definition
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any
from features.contracts import FeatureDefinition

@dataclass(frozen=True, slots=True)
class ShellFeatureDefinition(FeatureDefinition):
    source_body_id: str = ""
    output_id: str = ""
    thickness: float = -2.0
    tolerance: float = 0.01
    remove_face_indices: tuple[int, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_type(self) -> str:
        return "shell"

    def validate(self) -> None:
        FeatureDefinition.validate(self)
        for name, value in (
            ("source_body_id", self.source_body_id),
            ("output_id", self.output_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"ShellFeatureDefinition {name} cannot be empty.")
        if self.source_body_id == self.output_id:
            raise ValueError("Shell source_body_id and output_id must differ.")
        if isinstance(self.thickness, bool) or not isinstance(self.thickness, (int, float)):
            raise TypeError("Shell thickness must be numeric.")
        if not math.isfinite(float(self.thickness)) or self.thickness == 0:
            raise ValueError("Shell thickness must be finite and non-zero.")
        if isinstance(self.tolerance, bool) or not isinstance(self.tolerance, (int, float)):
            raise TypeError("Shell tolerance must be numeric.")
        if not math.isfinite(float(self.tolerance)) or self.tolerance <= 0:
            raise ValueError("Shell tolerance must be finite and greater than zero.")
        if not isinstance(self.remove_face_indices, tuple):
            raise TypeError("Shell remove_face_indices must be a tuple.")
        if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in self.remove_face_indices):
            raise ValueError("Shell remove_face_indices must contain non-negative integers.")
