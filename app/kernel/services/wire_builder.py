"""
DOBO CAD Kernel

Wire Builder

Converts backend-independent projected contours
into CadQuery Wire geometry.

This service is the explicit boundary between
mathematical geometry and the CAD backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import cadquery as cq

from kernel.contracts.projected_contour import (
    ProjectedContour,
)
from kernel.contracts.projected_contour_set import (
    ProjectedContourSet,
)


@dataclass(frozen=True, slots=True)
class WireBuildResult:
    """
    Result produced by WireBuilder.
    """

    wires: tuple[cq.Wire, ...]

    source: ProjectedContourSet

    @property
    def count(self) -> int:
        """
        Returns the number of generated Wires.
        """

        return len(
            self.wires
        )

    @property
    def is_empty(self) -> bool:
        """
        Returns True when no Wires were generated.
        """

        return self.count == 0

    def validate(self) -> None:
        """
        Validates all generated CAD Wires.
        """

        if self.is_empty:
            raise ValueError(
                "WireBuildResult cannot be empty."
            )

        self.source.validate()

        if self.count != self.source.count:
            raise ValueError(
                "WireBuildResult wire count must match "
                "the projected contour count."
            )

        for wire in self.wires:
            if not isinstance(
                wire,
                cq.Wire,
            ):
                raise TypeError(
                    "WireBuildResult contains a non-Wire object."
                )

            if not wire.isValid():
                raise ValueError(
                    "WireBuilder generated an invalid Wire."
                )


class WireBuilderInterface(ABC):
    """
    Public interface implemented by Wire Builders.
    """

    @abstractmethod
    def build(
        self,
        contours: ProjectedContourSet,
    ) -> WireBuildResult:
        """
        Builds CadQuery Wires from projected contours.
        """


class WireBuilder(WireBuilderInterface):
    """
    Default CadQuery Wire Builder.

    Each projected contour is converted directly into
    one ordered polygonal Wire.

    No resampling is performed.
    """

    def build(
        self,
        contours: ProjectedContourSet,
    ) -> WireBuildResult:
        """
        Builds one CadQuery Wire per projected contour.
        """

        contours.validate()

        wires = tuple(
            self._build_contour_wire(
                contour
            )
            for contour in contours.contours
        )

        result = WireBuildResult(
            wires=wires,
            source=contours,
        )

        result.validate()

        return result

    @staticmethod
    def _build_contour_wire(
        contour: ProjectedContour,
    ) -> cq.Wire:
        """
        Builds one polygonal Wire from ordered 3D points.
        """

        contour.validate()

        vectors = tuple(
            cq.Vector(
                point.x,
                point.y,
                point.z,
            )
            for point in contour.points
        )

        if contour.closed:
            wire = cq.Wire.makePolygon(
                list(
                    vectors
                ),
                close=True,
            )

        else:
            wire = cq.Wire.makePolygon(
                list(
                    vectors
                ),
                close=False,
            )

        if not isinstance(
            wire,
            cq.Wire,
        ):
            raise RuntimeError(
                "WireBuilder could not create "
                "a CadQuery Wire."
            )

        if not wire.isValid():
            raise RuntimeError(
                "WireBuilder created an invalid Wire."
            )

        return wire