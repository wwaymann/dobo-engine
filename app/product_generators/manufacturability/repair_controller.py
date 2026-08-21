from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, TypeVar

from .consolidated_validator import (
    ConsolidatedManufacturingReport,
    ValidationStatus,
)
from .contract import RULE_BY_CODE, RuleSeverity

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RepairCandidate(Generic[T]):
    rule_code: str
    label: str
    apply: Callable[[T], T]


@dataclass(frozen=True, slots=True)
class RepairAttempt(Generic[T]):
    candidate: RepairCandidate[T]
    accepted: bool
    before_blocking: int
    after_blocking: int


@dataclass(frozen=True, slots=True)
class RepairResult(Generic[T]):
    state: T
    report: ConsolidatedManufacturingReport
    attempts: tuple[RepairAttempt[T], ...]


class BoundedManufacturingRepairController(Generic[T]):
    """Apply deterministic repairs only when revalidation proves improvement.

    Guardrails:
    - SOURCE_PENDING and NOT_AVAILABLE are never treated as geometry failures.
    - each candidate is tried at most once;
    - accepted candidates may not introduce a new blocking error;
    - a repair of an ERROR rule must reduce the blocking-error count;
    - a repair of a WARNING rule must resolve that rule without regressing any
      previously-OK ERROR-severity rule;
    - every candidate is followed by a full 24-rule revalidation.
    """

    def __init__(self, *, max_attempts: int = 6) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self._max_attempts = int(max_attempts)

    @staticmethod
    def _by_code(report: ConsolidatedManufacturingReport) -> dict[str, ValidationStatus]:
        return {result.code: result.status for result in report.results}

    @staticmethod
    def _blocking_count(report: ConsolidatedManufacturingReport) -> int:
        return len(report.blocking_errors)

    @staticmethod
    def _eligible(status: ValidationStatus) -> bool:
        return status in {ValidationStatus.ERROR, ValidationStatus.WARNING}

    def repair(
        self,
        *,
        state: T,
        validate: Callable[[T], ConsolidatedManufacturingReport],
        candidates: Iterable[RepairCandidate[T]],
    ) -> RepairResult[T]:
        current_state = state
        current_report = validate(current_state)
        attempts: list[RepairAttempt[T]] = []

        for candidate in tuple(candidates)[: self._max_attempts]:
            before = self._by_code(current_report)
            current_status = before.get(candidate.rule_code)
            if current_status is None:
                raise KeyError(f"Unknown manufacturing rule: {candidate.rule_code}")
            if not self._eligible(current_status):
                continue

            proposed_state = candidate.apply(current_state)
            proposed_report = validate(proposed_state)
            after = self._by_code(proposed_report)

            before_blocking = self._blocking_count(current_report)
            after_blocking = self._blocking_count(proposed_report)
            severity = RULE_BY_CODE[candidate.rule_code].severity

            protected_error_rules = {
                code
                for code, status in before.items()
                if RULE_BY_CODE[code].severity is RuleSeverity.ERROR
                and status is ValidationStatus.OK
            }
            no_error_regression = all(
                after[code] is ValidationStatus.OK
                for code in protected_error_rules
            )

            if severity is RuleSeverity.ERROR:
                accepted = (
                    after_blocking < before_blocking
                    and no_error_regression
                )
            else:
                accepted = (
                    after[candidate.rule_code] is ValidationStatus.OK
                    and after_blocking <= before_blocking
                    and no_error_regression
                )

            attempts.append(
                RepairAttempt(
                    candidate=candidate,
                    accepted=accepted,
                    before_blocking=before_blocking,
                    after_blocking=after_blocking,
                )
            )

            if accepted:
                current_state = proposed_state
                current_report = proposed_report

        return RepairResult(
            state=current_state,
            report=current_report,
            attempts=tuple(attempts),
        )
