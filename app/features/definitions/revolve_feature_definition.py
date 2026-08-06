"""
DOBO Features

Revolve Feature Definition
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any
from features.contracts import BooleanMode, FeatureDefinition

Vector3 = tuple[float, float, float]

@dataclass(frozen=True, slots=True)
class RevolveFeatureDefinition(FeatureDefinition):
    region_set_id: str = ""
    region_id: str = ""
    output_id: str = ""
    angle: float = 360.0
    axis_origin: Vector3 = (0.0, 0.0, 0.0)
    axis_direction: Vector3 = (0.0, 1.0, 0.0)
    mode: BooleanMode = BooleanMode.NEW_BODY
    target_body_id: str | None = None
    merge: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_type(self) -> str:
        return "revolve"

    def validate(self) -> None:
        FeatureDefinition.validate(self)
        for name, value in (
            ("region_set_id", self.region_set_id),
            ("region_id", self.region_id),
            ("output_id", self.output_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"RevolveFeatureDefinition {name} cannot be empty.")
        if isinstance(self.angle, bool) or not isinstance(self.angle, (int, float)):
            raise TypeError("Revolve angle must be numeric.")
        if not math.isfinite(float(self.angle)) or not 0.0 < float(self.angle) <= 360.0:
            raise ValueError("Revolve angle must be greater than zero and at most 360.")
        self._validate_vector(self.axis_origin, "axis_origin", True)
        self._validate_vector(self.axis_direction, "axis_direction", False)
        if not isinstance(self.mode, BooleanMode):
            raise TypeError("Revolve mode must be BooleanMode.")
        if self.mode.requires_target_body and (
            self.target_body_id is None or not self.target_body_id.strip()
        ):
            raise ValueError("Boolean Revolve requires target_body_id.")
        if not isinstance(self.merge, bool):
            raise TypeError("Revolve merge must be boolean.")

    @staticmethod
    def _validate_vector(value: Vector3, name: str, allow_zero: bool) -> None:
        if not isinstance(value, tuple) or len(value) != 3:
            raise TypeError(f"{name} must be a 3-value tuple.")
        coordinates = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise TypeError(f"{name} values must be numeric.")
            numeric = float(item)
            if not math.isfinite(numeric):
                raise ValueError(f"{name} values must be finite.")
            coordinates.append(numeric)
        length = math.sqrt(sum(item * item for item in coordinates))
        if not allow_zero and length <= 1e-12:
            raise ValueError(f"{name} cannot be zero.")

    @property
    def normalized_axis_direction(self) -> Vector3:
        x, y, z = (float(item) for item in self.axis_direction)
        length = math.sqrt(x*x + y*y + z*z)
        return (x/length, y/length, z/length)
