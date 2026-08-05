from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4
from kernel.contracts.operations import KernelOperation
from .feature_definition import FeatureDefinition

@dataclass(frozen=True, slots=True)
class FeaturePlan:
    feature: FeatureDefinition
    operations: tuple[KernelOperation, ...]
    expected_output_ids: tuple[str, ...] = ()
    id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("FeaturePlan id cannot be empty.")
        if not isinstance(self.feature, FeatureDefinition):
            raise TypeError("FeaturePlan feature must inherit FeatureDefinition.")
        self.feature.validate()
        if not isinstance(self.operations, tuple) or not self.operations:
            raise ValueError("FeaturePlan requires at least one KernelOperation.")
        operation_ids: set[str] = set()
        declared_outputs: set[str] = set()
        for operation in self.operations:
            operation.validate()
            if operation.id in operation_ids:
                raise ValueError(f"Duplicate operation id '{operation.id}'.")
            operation_ids.add(operation.id)
            output_id = getattr(operation, "output_id", None)
            if output_id is not None:
                if not isinstance(output_id, str) or not output_id.strip():
                    raise ValueError("Operation output_id must be non-empty.")
                if output_id in declared_outputs:
                    raise ValueError(f"Duplicate output id '{output_id}'.")
                declared_outputs.add(output_id)
        if not isinstance(self.expected_output_ids, tuple):
            raise TypeError("expected_output_ids must be a tuple.")
        seen: set[str] = set()
        for output_id in self.expected_output_ids:
            if not isinstance(output_id, str) or not output_id.strip():
                raise ValueError("Expected output ids must be non-empty strings.")
            if output_id in seen:
                raise ValueError("expected_output_ids cannot contain duplicates.")
            if output_id not in declared_outputs:
                raise ValueError(f"Expected output '{output_id}' is not declared.")
            seen.add(output_id)
        if not isinstance(self.metadata, dict):
            raise TypeError("FeaturePlan metadata must be a dictionary.")

    @property
    def operation_count(self) -> int:
        return len(self.operations)

    @property
    def final_output_id(self) -> str | None:
        return self.expected_output_ids[-1] if self.expected_output_ids else None
