"""
DOBO Features

Shell Operation Builder
"""
from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.shell_feature_definition import ShellFeatureDefinition
from kernel.contracts.operations.shell_operation import ShellOperation
from .feature_operation_builder import FeatureOperationBuilder

class ShellOperationBuilder(FeatureOperationBuilder[ShellFeatureDefinition]):
    @property
    def feature_type(self) -> type[ShellFeatureDefinition]:
        return ShellFeatureDefinition

    def build(self, feature: ShellFeatureDefinition, context: FeatureContext) -> FeaturePlan:
        self.validate(feature, context)
        operation = ShellOperation(
            id=f"{feature.id}:shell-operation",
            name=feature.name,
            source_id=feature.source_body_id,
            output_id=feature.output_id,
            thickness=float(feature.thickness),
            tolerance=float(feature.tolerance),
            remove_face_indices=feature.remove_face_indices,
            metadata={"feature_id": feature.id, **feature.metadata},
        )
        operation.validate()
        plan = FeaturePlan(
            feature=feature,
            operations=(operation,),
            expected_output_ids=(feature.output_id,),
            metadata={"builder": "shell_operation_builder"},
        )
        plan.validate()
        return plan
