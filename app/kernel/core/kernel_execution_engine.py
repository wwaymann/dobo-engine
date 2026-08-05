"""
DOBO CAD Kernel

Kernel Execution Engine

Executes a validated KernelModel through the registered
operation executors and produces a complete
KernelExecutionResult.
"""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from kernel.contracts.operations import (
    KernelOperation,
)
from kernel.core.execution_context import (
    KernelExecutionContext,
)
from kernel.core.kernel_execution_result import (
    KernelExecutionResult,
    OperationExecutionResult,
    OperationExecutionStatus,
)
from kernel.core.kernel_model import KernelModel
from kernel.core.operation_dispatcher import (
    OperationDispatcher,
)
from kernel.core.operation_executor import (
    OperationExecutorPayload,
)


class KernelExecutionEngine:
    """
    Main orchestrator for the DOBO Kernel Core.

    Responsibilities:

    - validate KernelModel;
    - create KernelExecutionContext;
    - execute enabled operations in order;
    - collect per-operation results;
    - preserve generated solids and exports;
    - handle failures and skipped operations;
    - return KernelExecutionResult.

    Geometry algorithms remain inside the concrete
    operation executors.
    """

    def __init__(
        self,
        dispatcher: OperationDispatcher,
        *,
        stop_on_error: bool = True,
    ) -> None:
        """
        Creates a Kernel execution engine.

        stop_on_error=True:
            The first failed operation stops execution.
            Remaining enabled operations are marked
            as skipped.

        stop_on_error=False:
            Execution continues after failures.
        """

        if not isinstance(
            dispatcher,
            OperationDispatcher,
        ):
            raise TypeError(
                "KernelExecutionEngine requires "
                "an OperationDispatcher."
            )

        if not isinstance(
            stop_on_error,
            bool,
        ):
            raise TypeError(
                "KernelExecutionEngine stop_on_error "
                "must be boolean."
            )

        dispatcher.validate()

        self._dispatcher = dispatcher
        self._stop_on_error = stop_on_error

    def execute(
        self,
        model: KernelModel,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> KernelExecutionResult:
        """
        Executes one complete KernelModel.
        """

        if not isinstance(
            model,
            KernelModel,
        ):
            raise TypeError(
                "KernelExecutionEngine requires "
                "a KernelModel."
            )

        model.validate()
        self._dispatcher.validate()

        execution_metadata = (
            dict(
                metadata
            )
            if metadata is not None
            else {}
        )

        context = KernelExecutionContext(
            metadata={
                "model_id": model.id,
                "model_name": model.name,
                "stop_on_error": (
                    self._stop_on_error
                ),
                **model.metadata,
                **execution_metadata,
            },
        )

        started_at = datetime.now(
            UTC
        )

        execution_timer = perf_counter()

        operation_results: list[
            OperationExecutionResult
        ] = []

        enabled_operations = (
            model.enabled_operations
        )

        failure_detected = False

        for operation in enabled_operations:
            if (
                failure_detected
                and self._stop_on_error
            ):
                operation_results.append(
                    self._build_skipped_result(
                        operation=operation,
                        reason=(
                            "Skipped because a previous "
                            "operation failed."
                        ),
                    )
                )

                continue

            operation_result = (
                self._execute_operation(
                    operation=operation,
                    context=context,
                )
            )

            operation_results.append(
                operation_result
            )

            if operation_result.failed:
                failure_detected = True

        finished_at = datetime.now(
            UTC
        )

        duration_ms = (
            perf_counter()
            - execution_timer
        ) * 1000.0

        context.validate()

        result = KernelExecutionResult(
            model=model,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            operations=tuple(
                operation_results
            ),
            solids=context.solids.snapshot(),
            exports=tuple(
                context.exports
            ),
            metadata={
                **context.metadata,
                "context_id": context.id,
                "solid_count": context.solids.count,
                "export_count": context.export_count,
                "warning_count": context.warning_count,
                "log_count": context.log_count,
                "failed": failure_detected,
            },
        )

        result.validate()

        return result

    def _execute_operation(
        self,
        operation: KernelOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutionResult:
        """
        Executes one operation and captures its result.

        Exceptions produced by operation executors are
        converted into failed execution results.
        """

        operation.validate()

        started_at = datetime.now(
            UTC
        )

        timer = perf_counter()

        try:
            payload = self._dispatcher.dispatch(
                operation,
                context,
            )

            finished_at = datetime.now(
                UTC
            )

            duration_ms = (
                perf_counter()
                - timer
            ) * 1000.0

            return self._build_completed_result(
                operation=operation,
                payload=payload,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )

        except Exception as error:
            finished_at = datetime.now(
                UTC
            )

            duration_ms = (
                perf_counter()
                - timer
            ) * 1000.0

            return self._build_failed_result(
                operation=operation,
                error=error,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )

    @staticmethod
    def _build_completed_result(
        operation: KernelOperation,
        payload: OperationExecutorPayload,
        started_at: datetime,
        finished_at: datetime,
        duration_ms: float,
    ) -> OperationExecutionResult:
        """
        Builds one successful operation result.
        """

        payload.validate()

        result = OperationExecutionResult(
            operation=operation,
            status=(
                OperationExecutionStatus.COMPLETED
            ),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            output_id=payload.output_id,
            solid=payload.solid,
            export_path=payload.export_path,
            error_message=None,
            metadata={
                **payload.metadata,
                "produced_solid": (
                    payload.produced_solid
                ),
                "produced_export": (
                    payload.produced_export
                ),
                "warning_count": len(
                    payload.warnings
                ),
            },
        )

        result.validate()

        return result

    @staticmethod
    def _build_failed_result(
        operation: KernelOperation,
        error: Exception,
        started_at: datetime,
        finished_at: datetime,
        duration_ms: float,
    ) -> OperationExecutionResult:
        """
        Builds one failed operation result.
        """

        message = str(
            error
        ).strip()

        if not message:
            message = type(
                error
            ).__name__

        result = OperationExecutionResult(
            operation=operation,
            status=(
                OperationExecutionStatus.FAILED
            ),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            output_id=None,
            solid=None,
            export_path=None,
            error_message=message,
            metadata={
                "exception_type": (
                    type(
                        error
                    ).__name__
                ),
            },
        )

        result.validate()

        return result

    @staticmethod
    def _build_skipped_result(
        operation: KernelOperation,
        reason: str,
    ) -> OperationExecutionResult:
        """
        Builds one skipped operation result.
        """

        timestamp = datetime.now(
            UTC
        )

        result = OperationExecutionResult(
            operation=operation,
            status=(
                OperationExecutionStatus.SKIPPED
            ),
            started_at=timestamp,
            finished_at=timestamp,
            duration_ms=0.0,
            output_id=None,
            solid=None,
            export_path=None,
            error_message=None,
            metadata={
                "reason": reason,
            },
        )

        result.validate()

        return result

    @property
    def dispatcher(
        self,
    ) -> OperationDispatcher:
        """
        Returns the configured dispatcher.
        """

        return self._dispatcher

    @property
    def stop_on_error(self) -> bool:
        """
        Returns the configured failure behavior.
        """

        return self._stop_on_error