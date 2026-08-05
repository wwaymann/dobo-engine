from __future__ import annotations
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any
from kernel.contracts.solid import Solid
from .feature_definition import FeatureDefinition

@dataclass(frozen=True, slots=True)
class FeatureResult:
    feature: FeatureDefinition
    success: bool
    solid: Solid | None = None
    duration_ms: float = 0.0
    warnings: tuple[str, ...] = ()
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.feature, FeatureDefinition):
            raise TypeError("FeatureResult feature must inherit FeatureDefinition.")
        self.feature.validate()
        if not isinstance(self.success, bool):
            raise TypeError("FeatureResult success must be boolean.")
        if self.solid is not None:
            if not isinstance(self.solid, Solid):
                raise TypeError("FeatureResult solid must be a Kernel Solid.")
            self.solid.validate()
        if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, (int, float)):
            raise TypeError("duration_ms must be numeric.")
        if self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative.")
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple.")
        for warning in self.warnings:
            if not isinstance(warning, str) or not warning.strip():
                raise ValueError("warnings must contain non-empty strings.")
        if self.success and self.error_message is not None:
            raise ValueError("Successful result cannot contain error_message.")
        if not self.success and (self.error_message is None or not self.error_message.strip()):
            raise ValueError("Failed result requires error_message.")
        if not self.success and self.solid is not None:
            raise ValueError("Failed result cannot contain a Solid.")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

    @property
    def produced_solid(self) -> bool:
        return self.solid is not None

    @classmethod
    def success_result(cls, *, feature: FeatureDefinition, solid: Solid | None, started_at: float,
                       warnings: tuple[str, ...] = (), metadata: dict[str, Any] | None = None) -> "FeatureResult":
        result = cls(feature=feature, success=True, solid=solid,
                     duration_ms=(perf_counter() - started_at) * 1000.0,
                     warnings=warnings, metadata=dict(metadata or {}))
        result.validate()
        return result

    @classmethod
    def failure_result(cls, *, feature: FeatureDefinition, started_at: float, error_message: str,
                       warnings: tuple[str, ...] = (), metadata: dict[str, Any] | None = None) -> "FeatureResult":
        result = cls(feature=feature, success=False, solid=None,
                     duration_ms=(perf_counter() - started_at) * 1000.0,
                     warnings=warnings, error_message=error_message,
                     metadata=dict(metadata or {}))
        result.validate()
        return result
