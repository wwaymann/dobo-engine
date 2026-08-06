"""
DOBO CAD Kernel

Kernel Model

Stores and validates an ordered immutable-style sequence
of Kernel operations.

The model does not execute operations.
It only describes and validates the operation graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from kernel.contracts.operations import (
    BooleanOperation,
    ExportOperation,
    GeometryOperation,
    KernelOperation,
    ShellOperation,
)


@dataclass(slots=True)
class KernelModel:
    """
    Ordered parametric model definition.

    Operations are executed sequentially. Therefore,
    every referenced Solid must have been produced by
    an earlier enabled operation.
    """

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    name: str = ""

    operations: list[KernelOperation] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def add_operation(
        self,
        operation: KernelOperation,
    ) -> None:
        """
        Adds one operation after validating its
        immediate identifiers.
        """

        operation.validate()

        if self.has_operation_id(
            operation.id
        ):
            raise ValueError(
                "KernelModel already contains an "
                f"operation with id '{operation.id}'."
            )

        output_id = self._get_output_id(
            operation
        )

        if (
            output_id is not None
            and self.has_output_id(
                output_id
            )
        ):
            raise ValueError(
                "KernelModel already contains an "
                f"output with id '{output_id}'."
            )

        self.operations.append(
            operation
        )

    def insert_operation(
        self,
        index: int,
        operation: KernelOperation,
    ) -> None:
        """
        Inserts one operation at a specific position.
        """

        if isinstance(
            index,
            bool,
        ) or not isinstance(
            index,
            int,
        ):
            raise TypeError(
                "KernelModel operation index "
                "must be an integer."
            )

        if (
            index < 0
            or index > len(
                self.operations
            )
        ):
            raise IndexError(
                "KernelModel operation index "
                "is outside the valid range."
            )

        operation.validate()

        if self.has_operation_id(
            operation.id
        ):
            raise ValueError(
                "KernelModel already contains an "
                f"operation with id '{operation.id}'."
            )

        output_id = self._get_output_id(
            operation
        )

        if (
            output_id is not None
            and self.has_output_id(
                output_id
            )
        ):
            raise ValueError(
                "KernelModel already contains an "
                f"output with id '{output_id}'."
            )

        self.operations.insert(
            index,
            operation,
        )

    def remove_operation(
        self,
        operation_id: str,
    ) -> KernelOperation:
        """
        Removes and returns one operation.
        """

        index = self.index_of(
            operation_id
        )

        return self.operations.pop(
            index
        )

    def get_operation(
        self,
        operation_id: str,
    ) -> KernelOperation:
        """
        Returns one operation by identifier.
        """

        normalized_id = self._normalize_identifier(
            operation_id
        )

        for operation in self.operations:
            if operation.id == normalized_id:
                return operation

        raise KeyError(
            "KernelModel does not contain operation "
            f"'{operation_id}'."
        )

    def index_of(
        self,
        operation_id: str,
    ) -> int:
        """
        Returns the index of one operation.
        """

        normalized_id = self._normalize_identifier(
            operation_id
        )

        for index, operation in enumerate(
            self.operations
        ):
            if operation.id == normalized_id:
                return index

        raise KeyError(
            "KernelModel does not contain operation "
            f"'{operation_id}'."
        )

    def has_operation_id(
        self,
        operation_id: str,
    ) -> bool:
        """
        Returns whether an operation ID exists.
        """

        normalized_id = self._normalize_identifier(
            operation_id
        )

        return any(
            operation.id == normalized_id
            for operation in self.operations
        )

    def has_output_id(
        self,
        output_id: str,
    ) -> bool:
        """
        Returns whether an output ID is already declared.
        """

        normalized_id = self._normalize_identifier(
            output_id
        )

        return normalized_id in self.output_ids

    def validate(self) -> None:
        """
        Validates the complete ordered operation graph.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "KernelModel id cannot be empty."
            )

        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "KernelModel name must be a string."
            )

        if not isinstance(
            self.operations,
            list,
        ):
            raise TypeError(
                "KernelModel operations must be a list."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "KernelModel metadata must be a dictionary."
            )

        operation_ids: set[str] = set()

        available_outputs: set[str] = set()

        declared_outputs: set[str] = set()

        for index, operation in enumerate(
            self.operations
        ):
            operation.validate()

            if operation.id in operation_ids:
                raise ValueError(
                    "KernelModel contains duplicate "
                    f"operation id '{operation.id}'."
                )

            operation_ids.add(
                operation.id
            )

            if not operation.enabled:
                continue

            if isinstance(
                operation,
                GeometryOperation,
            ):
                self._validate_new_output(
                    output_id=operation.output_id,
                    declared_outputs=declared_outputs,
                    index=index,
                )

                available_outputs.add(
                    operation.output_id
                )

                declared_outputs.add(
                    operation.output_id
                )

                continue

            if isinstance(
                operation,
                BooleanOperation,
            ):
                self._require_available_output(
                    output_id=operation.target_id,
                    available_outputs=available_outputs,
                    operation=operation,
                    index=index,
                    role="target",
                )

                self._require_available_output(
                    output_id=operation.tool_id,
                    available_outputs=available_outputs,
                    operation=operation,
                    index=index,
                    role="tool",
                )

                self._validate_new_output(
                    output_id=operation.output_id,
                    declared_outputs=declared_outputs,
                    index=index,
                )

                available_outputs.add(
                    operation.output_id
                )

                declared_outputs.add(
                    operation.output_id
                )

                continue

            if isinstance(
                operation,
                ShellOperation,
            ):
                self._require_available_output(
                    output_id=operation.source_id,
                    available_outputs=available_outputs,
                    operation=operation,
                    index=index,
                    role="source",
                )

                self._validate_new_output(
                    output_id=operation.output_id,
                    declared_outputs=declared_outputs,
                    index=index,
                )

                available_outputs.add(
                    operation.output_id
                )

                declared_outputs.add(
                    operation.output_id
                )

                continue

            if isinstance(
                operation,
                ExportOperation,
            ):
                self._require_available_output(
                    output_id=operation.source_id,
                    available_outputs=available_outputs,
                    operation=operation,
                    index=index,
                    role="source",
                )

                continue

            raise TypeError(
                "KernelModel contains an unsupported "
                f"operation at index {index}."
            )

    @property
    def count(self) -> int:
        """
        Returns the total operation count.
        """

        return len(
            self.operations
        )

    @property
    def enabled_count(self) -> int:
        """
        Returns the enabled operation count.
        """

        return sum(
            1
            for operation in self.operations
            if operation.enabled
        )

    @property
    def operation_ids(
        self,
    ) -> tuple[str, ...]:
        """
        Returns operation IDs in execution order.
        """

        return tuple(
            operation.id
            for operation in self.operations
        )

    @property
    def output_ids(
        self,
    ) -> tuple[str, ...]:
        """
        Returns all declared Solid output IDs.
        """

        outputs: list[str] = []

        for operation in self.operations:
            output_id = self._get_output_id(
                operation
            )

            if output_id is not None:
                outputs.append(
                    output_id
                )

        return tuple(
            outputs
        )

    @property
    def enabled_operations(
        self,
    ) -> tuple[KernelOperation, ...]:
        """
        Returns enabled operations in execution order.
        """

        return tuple(
            operation
            for operation in self.operations
            if operation.enabled
        )

    @staticmethod
    def _get_output_id(
        operation: KernelOperation,
    ) -> str | None:
        """
        Returns the Solid output identifier declared
        by an operation.
        """

        if isinstance(
            operation,
            GeometryOperation,
        ):
            return operation.output_id

        if isinstance(
            operation,
            BooleanOperation,
        ):
            return operation.output_id

        if isinstance(
            operation,
            ShellOperation,
        ):
            return operation.output_id

        return None

    @staticmethod
    def _validate_new_output(
        output_id: str,
        declared_outputs: set[str],
        index: int,
    ) -> None:
        """
        Ensures a Solid output identifier is unique.
        """

        if output_id in declared_outputs:
            raise ValueError(
                "KernelModel operation at index "
                f"{index} declares duplicate output "
                f"'{output_id}'."
            )

    @staticmethod
    def _require_available_output(
        output_id: str,
        available_outputs: set[str],
        operation: KernelOperation,
        index: int,
        role: str,
    ) -> None:
        """
        Ensures an operation dependency was produced
        by an earlier enabled operation.
        """

        if output_id not in available_outputs:
            raise ValueError(
                "KernelModel operation "
                f"'{operation.display_name}' at index "
                f"{index} references unavailable {role} "
                f"output '{output_id}'."
            )

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        """
        Validates and normalizes one identifier.
        """

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "KernelModel identifier must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "KernelModel identifier cannot be empty."
            )

        return normalized
