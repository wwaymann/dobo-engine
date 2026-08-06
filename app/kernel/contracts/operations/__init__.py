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
from .shell_operation import (
    ShellOperation,
)


KernelOperation = (
    GeometryOperation
    | BooleanOperation
    | ShellOperation
    | ExportOperation
)


__all__ = [
    "OperationType",
    "BaseOperation",
    "GeometryOperation",
    "BooleanOperation",
    "ShellOperation",
    "ExportOperation",
    "KernelOperation",
]