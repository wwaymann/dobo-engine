"""
DOBO CAD Kernel

Polygon Provider

Generates one regular polygon contour.
"""

from __future__ import annotations

import cadquery as cq

from kernel.contracts.contour import Contour
from kernel.contracts.contour_set import ContourSet
from kernel.contracts.provider_request import ProviderRequest

from .provider import Provider


class PolygonProvider(Provider):
    """
    Generates one regular polygon contour.

    Required parameters:

    - sides
    - diameter

    Optional parameters:

    - rotation_degrees
    """

    @property
    def name(self) -> str:
        return "polygon"

    @property
    def aliases(self) -> tuple[str, ...]:
        return ("regular_polygon",)

    @property
    def description(self) -> str:
        return "Generates a regular polygon contour."

    def validate(
        self,
        request: ProviderRequest,
    ) -> None:
        """
        Validates polygon-specific parameters.
        """

        sides_value = request.get_parameter("sides")

        diameter_value = request.get_parameter("diameter")

        rotation_value = request.get_parameter(
            "rotation_degrees",
            0.0,
        )

        if sides_value is None:
            raise ValueError("PolygonProvider requires 'sides'.")

        if diameter_value is None:
            raise ValueError("PolygonProvider requires 'diameter'.")

        try:
            sides = int(sides_value)

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError("Polygon sides must be an integer.") from error

        try:
            diameter = float(diameter_value)

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError("Polygon diameter must be numeric.") from error

        try:
            float(rotation_value)

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError("Polygon rotation_degrees " "must be numeric.") from error

        if sides < 3:
            raise ValueError("Polygon sides must be at least 3.")

        if diameter <= 0:
            raise ValueError("Polygon diameter must be " "greater than zero.")

    def build_contours(
        self,
        request: ProviderRequest,
    ) -> ContourSet:
        """
        Generates a regular polygon ContourSet.
        """

        sides = int(request.get_parameter("sides"))

        diameter = float(request.get_parameter("diameter"))

        rotation_degrees = float(
            request.get_parameter(
                "rotation_degrees",
                0.0,
            )
        )

        polygon_workplane = cq.Workplane("XY").polygon(
            sides,
            diameter,
        )

        if rotation_degrees != 0:
            polygon_workplane = polygon_workplane.rotate(
                axisStartPoint=(
                    0.0,
                    0.0,
                    0.0,
                ),
                axisEndPoint=(
                    0.0,
                    0.0,
                    1.0,
                ),
                angleDegrees=rotation_degrees,
            )

        wire = polygon_workplane.val()

        if not isinstance(
            wire,
            cq.Shape,
        ):
            raise RuntimeError(
                "PolygonProvider could not " "generate polygon geometry."
            )

        contour = Contour(
            geometry=wire,
            source=self.name,
            metadata={
                "sides": sides,
                "diameter": diameter,
                "rotation_degrees": (rotation_degrees),
            },
        )

        return ContourSet(
            contours=[
                contour,
            ],
            source=self.name,
            metadata={
                "provider": self.name,
            },
        )
