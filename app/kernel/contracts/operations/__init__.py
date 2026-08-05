from .base_operation import (
    BaseOperation,
    OperationType,
)
from .boolean_operation import BooleanOperation
from .export_operation import ExportOperation
from .geometry_operation import GeometryOperation


KernelOperation = (
    GeometryOperation
    | BooleanOperation
    | ExportOperation
)


__all__ = [
    "OperationType",
    "BaseOperation",
    "GeometryOperation",
    "BooleanOperation",
    "ExportOperation",
    "KernelOperation",
]