"""
DOBO Features

Sweep Feature Definition
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from features.contracts import BooleanMode, FeatureDefinition

Vector3 = tuple[float, float, float]

@dataclass(frozen=True, slots=True)
class SweepFeatureDefinition(FeatureDefinition):
    region_set_id: str = ""
    region_id: str = ""
    path: tuple[Vector3, ...] = ()
    output_id: str = ""
    is_frenet: bool = False
    transition: str = "transformed"
    mode: BooleanMode = BooleanMode.NEW_BODY
    target_body_id: str | None = None
    merge: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_type(self) -> str:
        return "sweep"

    def validate(self) -> None:
        FeatureDefinition.validate(self)
        for name, value in (
            ("region_set_id", self.region_set_id),
            ("region_id", self.region_id),
            ("output_id", self.output_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"SweepFeatureDefinition {name} cannot be empty.")
        if not isinstance(self.path, tuple) or len(self.path) < 2:
            raise ValueError("Sweep path requires at least two points.")
        for index, point in enumerate(self.path):
            if not isinstance(point, tuple) or len(point) != 3:
                raise TypeError(f"Sweep path point {index} must be a 3-value tuple.")
            for value in point:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise TypeError("Sweep path values must be numeric.")
        if not isinstance(self.is_frenet, bool):
            raise TypeError("Sweep is_frenet must be boolean.")
        if self.transition not in ("transformed", "round", "right"):
            raise ValueError("Sweep transition is invalid.")
        if not isinstance(self.mode, BooleanMode):
            raise TypeError("Sweep mode must be BooleanMode.")
        if self.mode.requires_target_body and (
            self.target_body_id is None or not self.target_body_id.strip()
        ):
            raise ValueError("Boolean Sweep requires target_body_id.")
        if not isinstance(self.merge, bool):
            raise TypeError("Sweep merge must be boolean.")
