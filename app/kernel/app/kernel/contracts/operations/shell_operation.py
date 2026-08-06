"""
DOBO CAD Kernel

Shell Operation Contract
"""

from __future__ import annotations

from dataclasses import dataclass

from .base_operation import BaseOperation, OperationType


@dataclass(frozen=True, slots=True)
class ShellOperation(BaseOperation):
    """
    Hollows an existing Solid.

    source_id references a Solid already stored in the execution context.
    output_id receives the shelled result.
    """

    source_id: str = ""
    output_id: str = ""
    thickness: float = 1.0
    tolerance: float = 0.01
    remove_face_indices: tuple[int, ...] = ()

    @property
    def operation_type(self) -> OperationType:
        # Add SHELL to OperationType in base_operation.py.
        return OperationType.SHELL

    def validate(self) -> None:
        BaseOperation.validate(self)

        for name, value in (
            ("source_id", self.source_id),
            ("output_id", self.output_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"ShellOperation {name} cannot be empty.")

        if self.source_id == self.output_id:
            raise ValueError("ShellOperation source_id and output_id must differ.")

        if isinstance(self.thickness, bool) or not isinstance(
            self.thickness, (int, float)
        ):
            raise TypeError("ShellOperation thickness must be numeric.")

        if self.thickness == 0:
            raise ValueError("ShellOperation thickness cannot be zero.")

        if isinstance(self.tolerance, bool) or not isinstance(
            self.tolerance, (int, float)
        ):
            raise TypeError("ShellOperation tolerance must be numeric.")

        if self.tolerance <= 0:
            raise ValueError("ShellOperation tolerance must be greater than zero.")

        if not isinstance(self.remove_face_indices, tuple):
            raise TypeError("remove_face_indices must be a tuple.")

        if any(
            isinstance(index, bool) or not isinstance(index, int) or index < 0
            for index in self.remove_face_indices
        ):
            raise ValueError(
                "remove_face_indices must contain non-negative integers."
            )
