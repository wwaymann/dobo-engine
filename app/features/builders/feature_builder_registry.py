from __future__ import annotations
from typing import Any
from features.contracts import FeatureContext, FeatureDefinition, FeaturePlan
from .feature_operation_builder import FeatureOperationBuilder

BuilderType = FeatureOperationBuilder[Any]

class FeatureBuilderRegistry:
    def __init__(self) -> None:
        self._builders: dict[type[FeatureDefinition], BuilderType] = {}

    def register(self, builder: BuilderType) -> None:
        if not isinstance(builder, FeatureOperationBuilder):
            raise TypeError("Expected FeatureOperationBuilder.")
        feature_type = builder.feature_type
        if feature_type in self._builders:
            raise ValueError(f"Builder already registered for '{feature_type.__name__}'.")
        self._builders[feature_type] = builder

    def builder_for(self, feature: FeatureDefinition) -> BuilderType:
        if not isinstance(feature, FeatureDefinition):
            raise TypeError("Expected FeatureDefinition.")
        exact = self._builders.get(type(feature))
        if exact is not None:
            return exact
        for feature_type, builder in self._builders.items():
            if isinstance(feature, feature_type):
                return builder
        raise KeyError(f"No builder registered for '{type(feature).__name__}'.")

    def build(self, feature: FeatureDefinition, context: FeatureContext) -> FeaturePlan:
        feature.validate()
        context.validate()
        plan = self.builder_for(feature).build(feature, context)
        if not isinstance(plan, FeaturePlan):
            raise TypeError("Feature builders must return FeaturePlan.")
        plan.validate()
        return plan

    @property
    def count(self) -> int:
        return len(self._builders)
