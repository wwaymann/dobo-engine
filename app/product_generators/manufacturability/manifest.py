from __future__ import annotations

from dataclasses import dataclass

from .contract import (
    VALIDATION_RULES,
    ValidationDomain,
    ValidationRule,
)


@dataclass(frozen=True, slots=True)
class ValidationManifest:
    rules: tuple[ValidationRule, ...]

    @property
    def total(self) -> int:
        return len(self.rules)

    @property
    def implemented(self) -> int:
        return sum(
            1
            for rule in self.rules
            if rule.implementation_status.startswith(
                "implemented"
            )
        )

    @property
    def partial(self) -> int:
        return sum(
            1
            for rule in self.rules
            if (
                rule.implementation_status.startswith(
                    "partial"
                )
                or rule.implementation_status.endswith(
                    "pending"
                )
            )
        )

    @property
    def planned(self) -> int:
        return sum(
            1
            for rule in self.rules
            if rule.implementation_status == "planned"
        )

    def by_domain(
        self,
        domain: ValidationDomain,
    ) -> tuple[ValidationRule, ...]:
        return tuple(
            rule
            for rule in self.rules
            if rule.domain is domain
        )


DEFAULT_VALIDATION_MANIFEST = ValidationManifest(
    rules=VALIDATION_RULES
)
