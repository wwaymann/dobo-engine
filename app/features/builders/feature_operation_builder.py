from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from features.contracts import FeatureContext, FeatureDefinition, FeaturePlan

FeatureDefinitionT = TypeVar("FeatureDefinitionT", bound=FeatureDefinition)

class FeatureOperationBuilder(ABC, Generic[FeatureDefinitionT]):
    @property
    @abstractmethod
    def feature_type(self) -> type[FeatureDefinitionT]:
        ...

    @abstractmethod
    def build(self, feature: FeatureDefinitionT, context: FeatureContext) -> FeaturePlan:
        ...

    def validate(self, feature: FeatureDefinitionT, context: FeatureContext) -> None:
        if not isinstance(feature, self.feature_type):
            raise TypeError(f"{type(self).__name__} cannot build {type(feature).__name__}.")
        feature.validate()
        if not isinstance(context, FeatureContext):
            raise TypeError("FeatureOperationBuilder requires FeatureContext.")
        context.validate()
