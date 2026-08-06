from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.scale_feature_definition import ScaleFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class ScaleOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[ScaleFeatureDefinition]: return ScaleFeatureDefinition
    def build(self, feature:ScaleFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
