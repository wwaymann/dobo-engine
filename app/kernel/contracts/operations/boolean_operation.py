"""
DOBO CAD Kernel

Boolean Operation Contract

Describes how two named Solid results must be combined.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernel.contracts.boolean_request import (
    BooleanOperation as BooleanMode,
)

from .base_operation import (
    BaseOperation,
    OperationType,
)


@dataclass(frozen=True, slots=True)
class BooleanOperation(BaseOperation):
    """
    Combines two previously generated Solid results.

    target_id:
        Existing Solid used as the base operand.

    tool_id:
        Existing Solid applied to the target.

    output_id:
        Identifier assigned to the resulting Solid.
    """

    mode: BooleanMode = BooleanMode.UNION

    target_id: str = ""

    tool_id: str = ""

    output_id: str = ""

    tolerance: float = 0.01

    priority: int = 0

    @property
    def operation_type(self) -> OperationType:
        return OperationType.BOOLEAN

    def validate(self) -> None:
        """
        Validates the Boolean operation.
        """

        BaseOperation.validate(self)

        if not isinstance(
            self.mode,
            BooleanMode,
        ):
            raise TypeError(
                "BooleanOperation mode must be "
                "a BooleanMode value."
            )

        self._validate_identifier(
            value=self.target_id,
            field_name="target_id",
        )

        self._validate_identifier(
            value=self.tool_id,
            field_name="tool_id",
        )

        self._validate_identifier(
            value=self.output_id,
            field_name="output_id",
        )

        if self.target_id == self.tool_id:
            raise ValueError(
                "BooleanOperation target_id and tool_id "
                "must reference different solids."
            )

        if isinstance(
            self.tolerance,
            bool,
        ) or not isinstance(
            self.tolerance,
            (
                int,
                float,
            ),
        ):
            raise TypeError(
                "BooleanOperation tolerance "
                "must be numeric."
            )

        if self.tolerance <= 0:
            raise ValueError(
                "BooleanOperation tolerance "
                "must be greater than zero."
            )

        if isinstance(
            self.priority,
            bool,
        ) or not isinstance(
            self.priority,
            int,
        ):
            raise TypeError(
                "BooleanOperation priority "
                "must be an integer."
            )

    @staticmethod
    def _validate_identifier(
        value: str,
        field_name: str,
    ) -> None:
        """
        Validates one Solid registry identifier.
        """

        if not isinstance(
            value,
            str,
        ) or not value.strip():
            raise ValueError(
                f"BooleanOperation {field_name} "
                "cannot be empty."
            )