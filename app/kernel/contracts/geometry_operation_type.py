"""
DOBO CAD Kernel

Geometry Operation Type

Defines the geometric operation represented by a
GeometryRequest.
"""

from __future__ import annotations

from enum import Enum


class GeometryOperationType(str, Enum):
    """
    Supported backend-independent geometry operations.
    """

    EXTRUDE = "extrude"

    REVOLVE = "revolve"

    LOFT = "loft"

    SWEEP = "sweep"

    @property
    def requires_axis(self) -> bool:
        """
        Returns whether the operation requires an axis.
        """

        return self is GeometryOperationType.REVOLVE

    @property
    def requires_path(self) -> bool:
        """
        Returns whether the operation requires a path.
        """

        return self is GeometryOperationType.SWEEP

    @property
    def supports_multiple_sections(self) -> bool:
        """
        Returns whether multiple geometry sections
        may be required.
        """

        return self is GeometryOperationType.LOFT

    @classmethod
    def default(cls) -> "GeometryOperationType":
        """
        Returns the default geometry operation.
        """

        return cls.EXTRUDE