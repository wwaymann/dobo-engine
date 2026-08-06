"""
DOBO CAD Kernel

Geometry Result Contract

Represents the result produced by any
GeometryRequest executor.
"""

from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from typing import Any

import cadquery as cq

from kernel.contracts.geometry_request import (
    GeometryRequest,
)
from kernel.contracts.solid import (
    Solid,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GeometryResult:
    """
    Result produced by a GeometryRequest executor.
    """

    request: GeometryRequest

    solid: Solid

    generated_geometry: tuple[
        cq.Shape,
        ...
    ]

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete result.
        """

        self.request.validate()

        self.solid.validate()

        if not isinstance(
            self.generated_geometry,
            tuple,
        ):
            raise TypeError(
                "GeometryResult generated_geometry "
                "must be a tuple."
            )

        if not self.generated_geometry:
            raise ValueError(
                "GeometryResult requires at least "
                "one generated shape."
            )

        for geometry in self.generated_geometry:
            if not isinstance(
                geometry,
                cq.Shape,
            ):
                raise TypeError(
                    "GeometryResult contains "
                    "invalid geometry."
                )

            if not geometry.isValid():
                raise ValueError(
                    "GeometryResult contains "
                    "invalid CAD geometry."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "GeometryResult metadata "
                "must be a dictionary."
            )

    @property
    def geometry_count(
        self,
    ) -> int:
        """
        Number of generated geometries.
        """

        return len(
            self.generated_geometry
        )