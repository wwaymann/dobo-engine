"""
DOBO CAD Kernel

Geometry Request Executor Contract

Base interface implemented by all GeometryRequest
executors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from kernel.contracts.geometry_operation_type import (
    GeometryOperationType,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
)
from kernel.contracts.geometry_result import (
    GeometryResult,
)


class GeometryRequestExecutor(ABC):
    """
    Base class for every GeometryRequest executor.
    """

    @property
    @abstractmethod
    def operation_type(
        self,
    ) -> GeometryOperationType:
        """
        Geometry operation handled by this executor.
        """

    def supports(
        self,
        operation: GeometryOperationType,
    ) -> bool:
        """
        Returns whether this executor supports
        the requested operation.
        """

        if not isinstance(
            operation,
            GeometryOperationType,
        ):
            return False

        return operation is self.operation_type

    @abstractmethod
    def execute(
        self,
        request: GeometryRequest,
    ) -> GeometryResult:
        """
        Executes one GeometryRequest.
        """