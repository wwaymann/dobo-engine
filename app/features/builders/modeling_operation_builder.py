from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.modeling_feature_definition import ModelingFeatureDefinition
from kernel.contracts.operations.modeling_operation import ModelingOperation
from .feature_operation_builder import FeatureOperationBuilder

class ModelingOperationBuilder(FeatureOperationBuilder[ModelingFeatureDefinition]):
    @property
    def feature_type(self) -> type[ModelingFeatureDefinition]: return ModelingFeatureDefinition
    def build(self, feature:ModelingFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        self.validate(feature,context)
        operation=ModelingOperation(id=f'{feature.id}:modeling-operation',name=feature.name,
            source_id=feature.source_body_id,output_id=feature.output_id,tool=feature.tool,
            parameters=dict(feature.parameters),metadata={'feature_id':feature.id,**feature.metadata})
        operation.validate()
        plan=FeaturePlan(feature=feature,operations=(operation,),expected_output_ids=(feature.output_id,),metadata={'builder':'modeling_operation_builder','tool':feature.tool.value})
        plan.validate(); return plan
