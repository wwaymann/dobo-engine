from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CheckStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True, slots=True)
class ManufacturingCheck:
    code: str
    label: str
    status: CheckStatus
    message: str
    measured_value: float | None = None
    required_value: float | None = None
    unit: str | None = None
