from .base_operation import (
    BaseOperation,
    OperationType,
)
from .boolean_operation import (
    BooleanOperation,
)
from .export_operation import (
    ExportOperation,
)
from .geometry_operation import (
    GeometryOperation,
)
from .modeling_operation import (
    ModelingOperation,
    ModelingTool,
)
from .shell_operation import (
    ShellOperation,
)


KernelOperation = (
    GeometryOperation
    | BooleanOperation
    | ShellOperation
    | ModelingOperation
    | ExportOperation
)


__all__ = [
    "OperationType",
    "BaseOperation",
    "GeometryOperation",
    "BooleanOperation",
    "ShellOperation",
    "ModelingOperation",
    "ModelingTool",
    "ExportOperation",
    "KernelOperation",
]