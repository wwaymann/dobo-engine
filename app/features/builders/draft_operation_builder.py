from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.draft_feature_definition import DraftFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class DraftOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[DraftFeatureDefinition]: return DraftFeatureDefinition
    def build(self, feature:DraftFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
