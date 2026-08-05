"""DOBO CAD Kernel - shared execution context."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from kernel.contracts.operations import KernelOperation
from kernel.core.solid_registry import SolidRegistry


@dataclass(frozen=True, slots=True)
class ExecutionLogEntry:
    timestamp: datetime
    level: str
    message: str
    operation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError("ExecutionLogEntry timestamp must be a datetime.")
        if self.timestamp.tzinfo is None:
            raise ValueError("ExecutionLogEntry timestamp must be timezone-aware.")
        if self.level not in {"debug", "info", "warning", "error"}:
            raise ValueError("Invalid execution log level.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("ExecutionLogEntry message cannot be empty.")
        if self.operation_id is not None and (
            not isinstance(self.operation_id, str) or not self.operation_id.strip()
        ):
            raise ValueError("ExecutionLogEntry operation_id must be non-empty.")
        if not isinstance(self.metadata, dict):
            raise TypeError("ExecutionLogEntry metadata must be a dictionary.")


@dataclass(slots=True)
class KernelExecutionContext:
    """Mutable state shared by all operation executors in one run."""

    id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    solids: SolidRegistry = field(default_factory=SolidRegistry)
    exports: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    logs: list[ExecutionLogEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    active_operation_id: str | None = None

    def begin_operation(self, operation: KernelOperation) -> None:
        operation.validate()
        if self.active_operation_id is not None:
            raise RuntimeError("An operation is already active.")
        self.active_operation_id = operation.id
        self.log(
            level="debug",
            message=f"Operation started: {operation.display_name}",
            operation_id=operation.id,
            metadata={"operation_type": operation.operation_type.value},
        )

    def end_operation(self, operation: KernelOperation) -> None:
        operation.validate()
        if self.active_operation_id != operation.id:
            raise RuntimeError("Active operation does not match the operation being ended.")
        self.log(
            level="debug",
            message=f"Operation finished: {operation.display_name}",
            operation_id=operation.id,
        )
        self.active_operation_id = None

    def abort_operation(self, operation: KernelOperation, error: Exception) -> None:
        if self.active_operation_id == operation.id:
            self.active_operation_id = None
        self.log(
            level="error",
            message=str(error) or type(error).__name__,
            operation_id=operation.id,
            metadata={"exception_type": type(error).__name__},
        )

    def add_export(self, path: str) -> None:
        self.exports.append(self._normalize_text(path, "export path"))

    def add_warning(
        self,
        message: str,
        *,
        operation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        normalized = self._normalize_text(message, "warning")
        self.warnings.append(normalized)
        self.log(
            level="warning",
            message=normalized,
            operation_id=operation_id,
            metadata=metadata,
        )

    def log(
        self,
        *,
        level: str,
        message: str,
        operation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionLogEntry:
        entry = ExecutionLogEntry(
            timestamp=datetime.now(UTC),
            level=level.strip().lower(),
            message=message,
            operation_id=operation_id,
            metadata=dict(metadata) if metadata is not None else {},
        )
        entry.validate()
        self.logs.append(entry)
        return entry

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("KernelExecutionContext id cannot be empty.")
        if not isinstance(self.started_at, datetime):
            raise TypeError("KernelExecutionContext started_at must be a datetime.")
        if self.started_at.tzinfo is None:
            raise ValueError("KernelExecutionContext started_at must be timezone-aware.")
        self.solids.validate()
        for path in self.exports:
            self._normalize_text(path, "export path")
        for warning in self.warnings:
            self._normalize_text(warning, "warning")
        for entry in self.logs:
            entry.validate()
        if not isinstance(self.metadata, dict):
            raise TypeError("KernelExecutionContext metadata must be a dictionary.")

    @property
    def export_count(self) -> int:
        return len(self.exports)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def log_count(self) -> int:
        return len(self.logs)

    @property
    def elapsed_ms(self) -> float:
        return (datetime.now(UTC) - self.started_at).total_seconds() * 1000.0

    @staticmethod
    def _normalize_text(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"KernelExecutionContext {field_name} must be a string.")
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"KernelExecutionContext {field_name} cannot be empty.")
        return normalized