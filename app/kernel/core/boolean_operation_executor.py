"""
DOBO CAD Kernel

Boolean Operation Executor

Executes BooleanOperation objects using solids stored
inside KernelExecutionContext.
"""

from __future__ import annotations

from kernel.contracts.boolean_request import BooleanRequest
from kernel.contracts.model_state import ModelState
from kernel.contracts.operations import BooleanOperation
from kernel.core.execution_context import KernelExecutionContext
from kernel.core.operation_executor import (
    OperationExecutor,
    OperationExecutorPayload,
)
from kernel.services.boolean_engine import (
    BooleanEngineInterface,
)


class BooleanOperationExecutor(
    OperationExecutor[BooleanOperation],
):
    """
    Resolves two named solids from the execution context
    and combines them through BooleanEngine.
    """

    def __init__(
        self,
        boolean_engine: BooleanEngineInterface,
    ) -> None:
        if not isinstance(
            boolean_engine,
            BooleanEngineInterface,
        ):
            raise TypeError(
                "BooleanOperationExecutor requires "
                "a BooleanEngineInterface."
            )

        self._boolean_engine = boolean_engine

    @property
    def operation_class(
        self,
    ) -> type[BooleanOperation]:
        return BooleanOperation

    def _execute(
        self,
        operation: BooleanOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """
        Executes one Boolean operation.
        """

        operation.validate()
        context.validate()

        target = context.solids.get(
            operation.target_id
        )

        tool = context.solids.get(
            operation.tool_id
        )

        model = ModelState(
            solid=target,
            metadata={
                "target_id": operation.target_id,
            },
        )

        request = BooleanRequest(
            operation=operation.mode,
            operand=tool,
            tolerance=operation.tolerance,
            priority=operation.priority,
            label=operation.display_name,
            metadata={
                "kernel_operation_id": operation.id,
                "target_id": operation.target_id,
                "tool_id": operation.tool_id,
                **operation.metadata,
            },
        )

        result_state = self._boolean_engine.apply(
            model=model,
            request=request,
        )

        result_state.validate()

        result_solid = result_state.solid

        if result_solid is None:
            raise RuntimeError(
                "BooleanOperationExecutor produced "
                "an empty ModelState."
            )

        context.log(
            level="info",
            message=(
                "Boolean operation generated "
                f"solid '{operation.output_id}'."
            ),
            operation_id=operation.id,
            metadata={
                "mode": operation.mode.value,
                "target_id": operation.target_id,
                "tool_id": operation.tool_id,
                "output_id": operation.output_id,
                "volume": result_solid.volume,
                "model_version": result_state.version,
            },
        )

        return OperationExecutorPayload(
            output_id=operation.output_id,
            solid=result_solid,
            metadata={
                "executor": (
                    "boolean_operation_executor"
                ),
                "mode": operation.mode.value,
                "target_id": operation.target_id,
                "tool_id": operation.tool_id,
                "model_version": result_state.version,
                "history_count": (
                    result_state.operation_count
                ),
                "volume": result_solid.volume,
            },
        )