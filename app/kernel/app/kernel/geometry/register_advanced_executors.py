"""
Registers advanced GeometryRequest executors.
"""

from __future__ import annotations

from kernel.geometry.geometry_request_executor_registry import (
    GeometryRequestExecutorRegistry,
)

from .loft_request_executor import LoftRequestExecutor
from .revolve_request_executor import RevolveRequestExecutor
from .sweep_request_executor import SweepRequestExecutor


def register_advanced_executors(
    registry: GeometryRequestExecutorRegistry,
) -> GeometryRequestExecutorRegistry:
    registry.register(RevolveRequestExecutor())
    registry.register(LoftRequestExecutor())
    registry.register(SweepRequestExecutor())
    registry.validate()
    return registry
