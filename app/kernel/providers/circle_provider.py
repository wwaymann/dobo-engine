"""
DOBO CAD Kernel

Circle Provider

Reference implementation of a geometry Provider.
"""

from __future__ import annotations

import cadquery as cq

from kernel.contracts.contour import Contour
from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest

from .provider import Provider


class CircleProvider(Provider):
    """
    Generates one circular contour.
    """

    @property
    def name(self) -> str:
        return "circle"

    @property
    def description(self) -> str:
        return "Generates a circular contour."

    def validate(
        self,
        request: ProviderRequest,
    ) -> None:

        radius = request.get_parameter("radius")

        if radius is None:
            raise ValueError(
                "CircleProvider requires 'radius'."
            )

        if radius <= 0:
            raise ValueError(
                "Circle radius must be greater than zero."
            )

    def build_contours(
        self,
        request: ProviderRequest,
    ) -> ContourSet:

        radius = float(
            request.get_parameter("radius")
        )

        wire = (
            cq.Workplane("XY")
            .circle(radius)
            .wire()
            .val()
        )

        contour = Contour(
            geometry=wire,
            source=self.name,
        )

        return ContourSet(
            contours=[contour],
            source=self.name,
        )