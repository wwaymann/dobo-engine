"""
DOBO CAD Kernel

BooleanRequest Contract

Defines how a Solid must interact with the current ModelState.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from .solid import Solid


class BooleanOperation(str, Enum):
    """
    Boolean operations supported by the Kernel.
    """

    UNION = "union"
    CUT = "cut"
    INTERSECT = "intersect"


@dataclass(frozen=True, slots=True)
class BooleanRequest:
    """
    Describes one boolean operation.

    The BooleanRequest contains no model logic.
    It only defines the requested operation
    and the Solid operand.
    """

    id: str = field(default_factory=lambda: str(uuid4()))

    operation: BooleanOperation = BooleanOperation.UNION

    operand: Solid | None = None

    tolerance: float = 0.01

    priority: int = 0

    label: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validates the boolean request.
        """

        if self.operand is None:
            raise ValueError("BooleanRequest requires a Solid operand.")

        self.operand.validate()

        if self.tolerance <= 0:
            raise ValueError("BooleanRequest tolerance must be " "greater than zero.")

    @property
    def is_union(self) -> bool:
        """
        Returns True for a union operation.
        """

        return self.operation == BooleanOperation.UNION

    @property
    def is_cut(self) -> bool:
        """
        Returns True for a cut operation.
        """

        return self.operation == BooleanOperation.CUT

    @property
    def is_intersection(self) -> bool:
        """
        Returns True for an intersection operation.
        """

        return self.operation == BooleanOperation.INTERSECT
