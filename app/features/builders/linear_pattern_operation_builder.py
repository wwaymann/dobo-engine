from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.linear_pattern_feature_definition import LinearPatternFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class LinearPatternOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[LinearPatternFeatureDefinition]: return LinearPatternFeatureDefinition
    def build(self, feature:LinearPatternFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
