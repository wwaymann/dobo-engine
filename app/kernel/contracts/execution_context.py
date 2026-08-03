"""
DOBO CAD Kernel

ExecutionContext Contract

Contains runtime information shared by the Pipeline
during one execution.

ExecutionContext never contains geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ExecutionWarning:
    """
    Non-fatal warning generated during execution.
    """

    stage: str

    message: str

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionError:
    """
    Error generated during execution.
    """

    stage: str

    message: str

    exception_type: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StageExecution:
    """
    Statistics for one executed stage.
    """

    name: str

    started_at: datetime

    finished_at: datetime

    duration_ms: float

    objects_generated: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """
    Runtime execution context.

    Contains execution information only.

    Never contains CAD geometry.
    """

    id: str = field(default_factory=lambda: str(uuid4()))

    started_at: datetime = field(default_factory=datetime.utcnow)

    finished_at: datetime | None = None

    warnings: tuple[ExecutionWarning, ...] = ()

    errors: tuple[ExecutionError, ...] = ()

    executed_stages: tuple[StageExecution, ...] = ()

    statistics: dict[str, Any] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validates the execution context.
        """

        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at.")

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def stage_count(self) -> int:
        return len(self.executed_stages)

    @property
    def duration_ms(self) -> float | None:
        """
        Returns the total execution time.
        """

        if self.finished_at is None:
            return None

        delta = self.finished_at - self.started_at

        return delta.total_seconds() * 1000.0
