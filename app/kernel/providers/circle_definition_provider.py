"""
DOBO CAD Kernel

Circle Definition Provider

Produces backend-independent mathematical geometry.

No CadQuery or OpenCascade objects are generated here.
"""

from __future__ import annotations

import math

from kernel.contracts.contour_definition import (
    ContourDefinition,
)
from kernel.contracts.contour_definition_set import (
    ContourDefinitionSet,
)
from kernel.contracts.provider_request import (
    ProviderRequest,
)


class CircleDefinitionProvider:
    """
    Generates one circular ContourDefinition.

    This provider temporarily remains independent from
    the legacy Provider interface because that interface
    returns CadQuery-backed ContourSet objects.
    """

    @property
    def name(self) -> str:
        """
        Unique provider identifier.
        """

        return "circle_definition"

    @property
    def aliases(self) -> tuple[str, ...]:
        """
        Alternative provider identifiers.
        """

        return ()

    @property
    def version(self) -> str:
        """
        Provider version.
        """

        return "1.0.0"

    @property
    def description(self) -> str:
        """
        Human-readable provider description.
        """

        return (
            "Generates a backend-independent "
            "circular contour definition."
        )

    def validate(
        self,
        request: ProviderRequest,
    ) -> None:
        """
        Validates circle-specific parameters.
        """

        request.validate()

        if (
            request.provider.strip().lower()
            != self.name
        ):
            raise ValueError(
                "ProviderRequest targets "
                f"'{request.provider}', but this provider "
                f"is '{self.name}'."
            )

        radius_value = request.get_parameter(
            "radius"
        )

        samples_value = request.get_parameter(
            "samples",
            128,
        )

        if radius_value is None:
            raise ValueError(
                "CircleDefinitionProvider requires "
                "'radius'."
            )

        if isinstance(
            radius_value,
            bool,
        ) or not isinstance(
            radius_value,
            (
                int,
                float,
                str,
            ),
        ):
            raise ValueError(
                "Circle radius must be numeric."
            )

        try:
            radius = float(
                radius_value
            )

        except ValueError as error:
            raise ValueError(
                "Circle radius must be numeric."
            ) from error

        if radius <= 0:
            raise ValueError(
                "Circle radius must be greater than zero."
            )

        if isinstance(
            samples_value,
            bool,
        ) or not isinstance(
            samples_value,
            (
                int,
                float,
                str,
            ),
        ):
            raise ValueError(
                "Circle samples must be an integer."
            )

        try:
            samples_float = float(
                samples_value
            )

        except ValueError as error:
            raise ValueError(
                "Circle samples must be numeric."
            ) from error

        if not samples_float.is_integer():
            raise ValueError(
                "Circle samples must be a whole number."
            )

        samples = int(
            samples_float
        )

        if samples < 8:
            raise ValueError(
                "Circle samples must be at least 8."
            )

    def execute(
        self,
        request: ProviderRequest,
    ) -> ContourDefinitionSet:
        """
        Generates a circular ContourDefinitionSet.
        """

        self.validate(
            request
        )

        radius = float(
            request.get_parameter(
                "radius"
            )
        )

        samples = int(
            float(
                request.get_parameter(
                    "samples",
                    128,
                )
            )
        )

        points = tuple(
            (
                float(
                    radius
                    * math.cos(
                        2.0
                        * math.pi
                        * index
                        / samples
                    )
                ),
                float(
                    radius
                    * math.sin(
                        2.0
                        * math.pi
                        * index
                        / samples
                    )
                ),
            )
            for index in range(
                samples
            )
        )

        contour = ContourDefinition(
            points=points,
            closed=True,
            source=self.name,
            metadata={
                "radius": radius,
                "samples": samples,
            },
        )

        contour.validate()

        result = ContourDefinitionSet(
            contours=(
                contour,
            ),
            source=self.name,
            metadata={
                "provider": self.name,
            },
        )

        result.validate()

        return result