from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import cadquery as cq


class SurfaceDesignMode(str, Enum):
    EMBOSS = "emboss"
    DEBOSS = "deboss"


@dataclass(frozen=True, slots=True)
class SurfaceDesignResult:
    shape: cq.Shape
    operation: str
    source_kind: str
    metadata: dict[str, object]

    def validate(self) -> None:
        if not isinstance(self.shape, cq.Shape):
            raise TypeError("shape must be a CadQuery Shape.")

        if not self.shape.isValid():
            raise RuntimeError(
                "SurfaceDesignResult contains invalid geometry."
            )

        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("operation cannot be empty.")

        if not isinstance(self.source_kind, str) or not self.source_kind.strip():
            raise ValueError("source_kind cannot be empty.")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")
