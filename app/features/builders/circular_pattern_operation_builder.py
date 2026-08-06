from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.circular_pattern_feature_definition import CircularPatternFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class CircularPatternOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[CircularPatternFeatureDefinition]: return CircularPatternFeatureDefinition
    def build(self, feature:CircularPatternFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
