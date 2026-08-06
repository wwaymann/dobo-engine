from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.mirror_feature_definition import MirrorFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class MirrorOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[MirrorFeatureDefinition]: return MirrorFeatureDefinition
    def build(self, feature:MirrorFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
