from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from .base_operation import BaseOperation, OperationType

class ModelingTool(str, Enum):
    MOVE='move'; ROTATE='rotate'; SCALE='scale'; MIRROR='mirror'
    FILLET='fillet'; CHAMFER='chamfer'; DRAFT='draft'
    LINEAR_PATTERN='linear_pattern'; CIRCULAR_PATTERN='circular_pattern'

@dataclass(frozen=True, slots=True)
class ModelingOperation(BaseOperation):
    source_id: str=''
    output_id: str=''
    tool: ModelingTool=ModelingTool.MOVE
    parameters: dict[str, Any]=field(default_factory=dict)

    @property
    def operation_type(self) -> OperationType:
        return OperationType.MODELING

    def validate(self) -> None:
        BaseOperation.validate(self)
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError('ModelingOperation source_id cannot be empty.')
        if not isinstance(self.output_id, str) or not self.output_id.strip():
            raise ValueError('ModelingOperation output_id cannot be empty.')
        if self.source_id == self.output_id:
            raise ValueError('source_id and output_id must differ.')
        if not isinstance(self.tool, ModelingTool):
            raise TypeError('tool must be ModelingTool.')
        if not isinstance(self.parameters, dict):
            raise TypeError('parameters must be a dictionary.')
