from __future__ import annotations
from dataclasses import dataclass
from kernel.contracts.operations.modeling_operation import ModelingTool
from .modeling_feature_definition import ModelingFeatureDefinition

@dataclass(frozen=True, slots=True)
class RotateFeatureDefinition(ModelingFeatureDefinition):
    tool: ModelingTool = ModelingTool.ROTATE
