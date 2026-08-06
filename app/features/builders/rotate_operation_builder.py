from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.rotate_feature_definition import RotateFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class RotateOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[RotateFeatureDefinition]: return RotateFeatureDefinition
    def build(self, feature:RotateFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
