from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from features.contracts import FeatureDefinition
from kernel.contracts.operations.modeling_operation import ModelingTool

@dataclass(frozen=True, slots=True)
class ModelingFeatureDefinition(FeatureDefinition):
    source_body_id: str=''
    output_id: str=''
    tool: ModelingTool=ModelingTool.MOVE
    parameters: dict[str, Any]=field(default_factory=dict)
    metadata: dict[str, Any]=field(default_factory=dict)

    @property
    def feature_type(self) -> str: return self.tool.value
    def validate(self) -> None:
        FeatureDefinition.validate(self)
        if not isinstance(self.source_body_id,str) or not self.source_body_id.strip(): raise ValueError('source_body_id cannot be empty')
        if not isinstance(self.output_id,str) or not self.output_id.strip(): raise ValueError('output_id cannot be empty')
        if self.source_body_id==self.output_id: raise ValueError('source_body_id and output_id must differ')
        if not isinstance(self.tool,ModelingTool): raise TypeError('tool must be ModelingTool')
        if not isinstance(self.parameters,dict): raise TypeError('parameters must be a dictionary')
