from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.fillet_feature_definition import FilletFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class FilletOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[FilletFeatureDefinition]: return FilletFeatureDefinition
    def build(self, feature:FilletFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
