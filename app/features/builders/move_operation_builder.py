from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.move_feature_definition import MoveFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class MoveOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[MoveFeatureDefinition]: return MoveFeatureDefinition
    def build(self, feature:MoveFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
