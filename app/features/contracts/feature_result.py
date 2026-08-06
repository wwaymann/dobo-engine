"""
DOBO Features

Feature Result Contract

Represents the final result produced by Feature
execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Self

from kernel.contracts.solid import Solid

from .feature_definition import FeatureDefinition
from .feature_plan import FeaturePlan


@dataclass(frozen=True, slots=True)
class FeatureResult:
    """
    Final result produced by one Feature execution.
    """

    feature: FeatureDefinition

    success: bool

    plan: FeaturePlan | None = None

    solid: Solid | None = None

    output_id: str | None = None

    duration_ms: float = 0.0

    warnings: tuple[str, ...] = ()

    error_message: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete Feature result.
        """

        if not isinstance(
            self.feature,
            FeatureDefinition,
        ):
            raise TypeError(
                "FeatureResult feature must inherit "
                "FeatureDefinition."
            )

        self.feature.validate()

        if not isinstance(
            self.success,
            bool,
        ):
            raise TypeError(
                "FeatureResult success must be boolean."
            )

        if self.plan is not None:
            if not isinstance(
                self.plan,
                FeaturePlan,
            ):
                raise TypeError(
                    "FeatureResult plan must be "
                    "FeaturePlan."
                )

            self.plan.validate()

            if self.plan.feature is not self.feature:
                raise ValueError(
                    "FeatureResult plan must reference "
                    "the source FeatureDefinition."
                )

        if self.solid is not None:
            if not isinstance(
                self.solid,
                Solid,
            ):
                raise TypeError(
                    "FeatureResult solid must be "
                    "a Kernel Solid."
                )

            self.solid.validate()

        if self.output_id is not None:
            if not isinstance(
                self.output_id,
                str,
            ) or not self.output_id.strip():
                raise ValueError(
                    "FeatureResult output_id must be "
                    "a non-empty string."
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
            raise TypeError(
                "FeatureResult duration_ms "
                "must be numeric."
            )

        if self.duration_ms < 0.0:
            raise ValueError(
                "FeatureResult duration_ms "
                "cannot be negative."
            )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "FeatureResult warnings must be "
                "a tuple."
            )

        for warning in self.warnings:
            if not isinstance(
                warning,
                str,
            ) or not warning.strip():
                raise ValueError(
                    "FeatureResult warnings must contain "
                    "non-empty strings."
                )

        if self.success:
            if self.error_message is not None:
                raise ValueError(
                    "Successful FeatureResult cannot "
                    "contain error_message."
                )

            if self.plan is None:
                raise ValueError(
                    "Successful FeatureResult requires "
                    "a FeaturePlan."
                )

            if (
                self.output_id is not None
                and self.plan.final_output_id
                != self.output_id
            ):
                raise ValueError(
                    "FeatureResult output_id must match "
                    "FeaturePlan final_output_id."
                )

        else:
            if (
                not isinstance(
                    self.error_message,
                    str,
                )
                or not self.error_message.strip()
            ):
                raise ValueError(
                    "Failed FeatureResult requires "
                    "error_message."
                )

            if self.solid is not None:
                raise ValueError(
                    "Failed FeatureResult cannot "
                    "contain a Solid."
                )

            if self.output_id is not None:
                raise ValueError(
                    "Failed FeatureResult cannot "
                    "contain output_id."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "FeatureResult metadata must be "
                "a dictionary."
            )

    @property
    def succeeded(self) -> bool:
        """
        Returns whether execution succeeded.
        """

        return self.success

    @property
    def failed(self) -> bool:
        """
        Returns whether execution failed.
        """

        return not self.success

    @property
    def produced_solid(self) -> bool:
        """
        Returns whether execution produced a Solid.
        """

        return self.solid is not None

    @property
    def operation_count(self) -> int:
        """
        Returns the number of planned Kernel operations.
        """

        if self.plan is None:
            return 0

        return self.plan.operation_count

    @classmethod
    def success_result(
        cls,
        *,
        feature: FeatureDefinition,
        plan: FeaturePlan,
        solid: Solid | None,
        output_id: str | None,
        started_at: float,
        warnings: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Self:
        """
        Creates a validated successful result.
        """

        result = cls(
            feature=feature,
            success=True,
            plan=plan,
            solid=solid,
            output_id=output_id,
            duration_ms=(
                perf_counter()
                - started_at
            )
            * 1000.0,
            warnings=warnings,
            error_message=None,
            metadata=dict(
                metadata or {}
            ),
        )

        result.validate()

        return result

    @classmethod
    def failure_result(
        cls,
        *,
        feature: FeatureDefinition,
        started_at: float,
        error_message: str,
        plan: FeaturePlan | None = None,
        warnings: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Self:
        """
        Creates a validated failed result.
        """

        result = cls(
            feature=feature,
            success=False,
            plan=plan,
            solid=None,
            output_id=None,
            duration_ms=(
                perf_counter()
                - started_at
            )
            * 1000.0,
            warnings=warnings,
            error_message=error_message,
            metadata=dict(
                metadata or {}
            ),
        )

        result.validate()

        return result