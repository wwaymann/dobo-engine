"""
DOBO CAD Kernel

Boolean Stage

Coordinates the Boolean Engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernel.contracts.boolean_request import (
    BooleanOperation,
    BooleanRequest,
)
from kernel.contracts.model_state import ModelState
from kernel.contracts.solid import Solid
from kernel.services.boolean_engine import (
    BooleanEngineInterface,
)


@dataclass(frozen=True, slots=True)
class BooleanStageResult:
    """
    Immutable result produced by BooleanStage.
    """

    model: ModelState
    request: BooleanRequest


class BooleanStage:
    """
    Coordinates the Boolean Engine.

    This stage creates the BooleanRequest and delegates
    the CAD operation to BooleanEngine.
    """

    def __init__(
        self,
        engine: BooleanEngineInterface,
    ) -> None:
        self._engine = engine

    def execute(
        self,
        model: ModelState,
        solid: Solid,
        operation: BooleanOperation,
        tolerance: float = 0.01,
        priority: int = 0,
        label: str = "",
        metadata: dict[str, object] | None = None,
    ) -> BooleanStageResult:
        """
        Executes one boolean operation.
        """

        model.validate()
        solid.validate()

        request = BooleanRequest(
            operation=operation,
            operand=solid,
            tolerance=tolerance,
            priority=priority,
            label=label,
            metadata=(
                metadata.copy()
                if metadata is not None
                else {}
            ),
        )

        request.validate()

        updated_model = self._engine.apply(
            model=model,
            request=request,
        )

        updated_model.validate()

        return BooleanStageResult(
            model=updated_model,
            request=request,
        )