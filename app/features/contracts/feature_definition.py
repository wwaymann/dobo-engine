from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

@dataclass(frozen=True, slots=True)
class FeatureDefinition(ABC):
    name: str
    id: str = field(default_factory=lambda: str(uuid4()))
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    @abstractmethod
    def feature_type(self) -> str:
        ...

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("FeatureDefinition id cannot be empty.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("FeatureDefinition name cannot be empty.")
        if not isinstance(self.enabled, bool):
            raise TypeError("FeatureDefinition enabled must be boolean.")
        if not isinstance(self.metadata, dict):
            raise TypeError("FeatureDefinition metadata must be a dictionary.")
        if not isinstance(self.feature_type, str) or not self.feature_type.strip():
            raise ValueError("FeatureDefinition feature_type cannot be empty.")

    @property
    def is_enabled(self) -> bool:
        return self.enabled
