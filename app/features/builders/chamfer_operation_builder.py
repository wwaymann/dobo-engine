from __future__ import annotations
from features.contracts import FeatureContext, FeaturePlan
from features.definitions.chamfer_feature_definition import ChamferFeatureDefinition
from .modeling_operation_builder import ModelingOperationBuilder

class ChamferOperationBuilder(ModelingOperationBuilder):
    @property
    def feature_type(self) -> type[ChamferFeatureDefinition]: return ChamferFeatureDefinition
    def build(self, feature:ChamferFeatureDefinition, context:FeatureContext) -> FeaturePlan:
        return super().build(feature,context)
