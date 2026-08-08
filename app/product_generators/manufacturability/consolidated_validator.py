from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contract import RULES, RULE_BY_CODE, RuleSeverity


class ValidationStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SOURCE_PENDING = "SOURCE_PENDING"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True, slots=True)
class RuleResult:
    code: str
    status: ValidationStatus
    note: str | None = None

    @property
    def blocking(self) -> bool:
        return (
            RULE_BY_CODE[self.code].severity == RuleSeverity.ERROR
            and self.status == ValidationStatus.ERROR
        )


@dataclass(frozen=True, slots=True)
class ConsolidatedManufacturingReport:
    results: tuple[RuleResult, ...]

    @property
    def blocking_errors(self) -> tuple[RuleResult, ...]:
        return tuple(
            result
            for result in self.results
            if result.blocking
        )

    def count(self, status: ValidationStatus) -> int:
        return sum(result.status == status for result in self.results)


class ManufacturingValidator:
    """
    Phase 7.9 consolidation layer.

    This class does not replace the analyzers from Phases 7.4-7.8.
    It consolidates their 24 contract outcomes into one report and guarantees
    that every rule appears exactly once.

    Use `from_status_map()` while wiring the existing analyzers into the final
    product pipeline.
    """

    def from_status_map(
        self,
        statuses: dict[str, ValidationStatus],
        notes: dict[str, str] | None = None,
    ) -> ConsolidatedManufacturingReport:
        notes = notes or {}

        expected = {rule.code for rule in RULES}
        supplied = set(statuses)

        missing = expected - supplied
        extra = supplied - expected

        if missing or extra:
            raise RuntimeError(
                "Manufacturing status map does not match 24-rule contract. "
                f"missing={sorted(missing)} extra={sorted(extra)}"
            )

        results = tuple(
            RuleResult(
                code=rule.code,
                status=statuses[rule.code],
                note=notes.get(rule.code),
            )
            for rule in RULES
        )

        return ConsolidatedManufacturingReport(results=results)
