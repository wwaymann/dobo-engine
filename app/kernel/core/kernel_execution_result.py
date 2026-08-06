"""
DOBO CAD Kernel

Kernel Execution Result

Stores the complete immutable result of a
KernelExecutionEngine run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from kernel.contracts.operations import (
    KernelOperation,
    OperationType,
)
from kernel.contracts.solid import Solid
from kernel.core.kernel_model import KernelModel


class OperationExecutionStatus(str, Enum):
    """
    Possible states of one operation execution.
    """

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OperationExecutionResult:
    """
    Result of one Kernel operation.
    """

    operation: KernelOperation

    status: OperationExecutionStatus

    started_at: datetime

    finished_at: datetime

    duration_ms: float

    output_id: str | None = None

    solid: Solid | None = None

    export_path: str | None = None

    error_message: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validates one operation execution result.
        """

        self.operation.validate()

        if not isinstance(
            self.status,
            OperationExecutionStatus,
        ):
            raise TypeError(
                "OperationExecutionResult status must be "
                "an OperationExecutionStatus."
            )

        if not isinstance(
            self.started_at,
            datetime,
        ):
            raise TypeError(
                "OperationExecutionResult started_at " "must be a datetime."
            )

        if not isinstance(
            self.finished_at,
            datetime,
        ):
            raise TypeError(
                "OperationExecutionResult finished_at " "must be a datetime."
            )

        if self.finished_at < self.started_at:
            raise ValueError(
                "OperationExecutionResult finished_at " "cannot precede started_at."
            )

        if isinstance(
            self.duration_ms,
            bool,
        ) or not isinstance(
            self.duration_ms,
            (
                int,
                float,
            ),
        ):
            raise TypeError("OperationExecutionResult duration_ms " "must be numeric.")

        if self.duration_ms < 0:
            raise ValueError(
                "OperationExecutionResult duration_ms " "cannot be negative."
            )

        if self.output_id is not None:
            if (
                not isinstance(
                    self.output_id,
                    str,
                )
                or not self.output_id.strip()
            ):
                raise ValueError(
                    "OperationExecutionResult output_id " "must be a non-empty string."
                )

        if self.solid is not None:
            self.solid.validate()

        if self.export_path is not None:
            if (
                not isinstance(
                    self.export_path,
                    str,
                )
                or not self.export_path.strip()
            ):
                raise ValueError(
                    "OperationExecutionResult export_path "
                    "must be a non-empty string."
                )

        if self.error_message is not None:
            if (
                not isinstance(
                    self.error_message,
                    str,
                )
                or not self.error_message.strip()
            ):
                raise ValueError(
                    "OperationExecutionResult error_message "
                    "must be a non-empty string."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "OperationExecutionResult metadata " "must be a dictionary."
            )

        if (
            self.status == OperationExecutionStatus.COMPLETED
            and self.error_message is not None
        ):
            raise ValueError(
                "Completed operation results cannot " "contain an error message."
            )

        if (
            self.status == OperationExecutionStatus.FAILED
            and self.error_message is None
        ):
            raise ValueError("Failed operation results require " "an error message.")

    @property
    def succeeded(self) -> bool:
        """
        Returns whether the operation completed.
        """

        return self.status == OperationExecutionStatus.COMPLETED

    @property
    def failed(self) -> bool:
        """
        Returns whether the operation failed.
        """

        return self.status == OperationExecutionStatus.FAILED

    @property
    def skipped(self) -> bool:
        """
        Returns whether the operation was skipped.
        """

        return self.status == OperationExecutionStatus.SKIPPED

    @property
    def operation_type(self) -> OperationType:
        """
        Returns the operation type.
        """

        return self.operation.operation_type


@dataclass(frozen=True, slots=True)
class KernelExecutionResult:
    """
    Complete result of one Kernel model execution.
    """

    model: KernelModel

    started_at: datetime

    finished_at: datetime

    duration_ms: float

    operations: tuple[
        OperationExecutionResult,
        ...,
    ]

    solids: dict[str, Solid] = field(default_factory=dict)

    exports: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validates the complete execution result.
        """

        self.model.validate()

        if not isinstance(
            self.started_at,
            datetime,
        ):
            raise TypeError("KernelExecutionResult started_at " "must be a datetime.")

        if not isinstance(
            self.finished_at,
            datetime,
        ):
            raise TypeError("KernelExecutionResult finished_at " "must be a datetime.")

        if self.finished_at < self.started_at:
            raise ValueError(
                "KernelExecutionResult finished_at " "cannot precede started_at."
            )

        if isinstance(
            self.duration_ms,
            bool,
        ) or not isinstance(
            self.duration_ms,
            (
                int,
                float,
            ),
        ):
            raise TypeError("KernelExecutionResult duration_ms " "must be numeric.")

        if self.duration_ms < 0:
            raise ValueError("KernelExecutionResult duration_ms " "cannot be negative.")

        if len(self.operations) != self.model.enabled_count:
            raise ValueError(
                "KernelExecutionResult operation count "
                "must match enabled model operations."
            )

        for operation_result in self.operations:
            operation_result.validate()

        if not isinstance(
            self.solids,
            dict,
        ):
            raise TypeError("KernelExecutionResult solids " "must be a dictionary.")

        for output_id, solid in self.solids.items():
            if (
                not isinstance(
                    output_id,
                    str,
                )
                or not output_id.strip()
            ):
                raise ValueError("KernelExecutionResult solid IDs " "cannot be empty.")

            solid.validate()

        for export_path in self.exports:
            if (
                not isinstance(
                    export_path,
                    str,
                )
                or not export_path.strip()
            ):
                raise ValueError(
                    "KernelExecutionResult exports " "must contain non-empty strings."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError("KernelExecutionResult metadata " "must be a dictionary.")

    @property
    def operation_count(self) -> int:
        """
        Returns the executed operation count.
        """

        return len(self.operations)

    @property
    def completed_count(self) -> int:
        """
        Returns the successful operation count.
        """

        return sum(1 for result in self.operations if result.succeeded)

    @property
    def failed_count(self) -> int:
        """
        Returns the failed operation count.
        """

        return sum(1 for result in self.operations if result.failed)

    @property
    def skipped_count(self) -> int:
        """
        Returns the skipped operation count.
        """

        return sum(1 for result in self.operations if result.skipped)

    @property
    def succeeded(self) -> bool:
        """
        Returns whether the complete execution succeeded.
        """

        return self.failed_count == 0 and self.completed_count == self.operation_count

    @property
    def final_solid(self) -> Solid | None:
        """
        Returns the latest generated Solid.
        """

        if not self.solids:
            return None

        return tuple(self.solids.values())[-1]
