"""
DOBO CAD Kernel

Geometry Request Test
"""

from __future__ import annotations

from kernel.contracts.geometry_definition import (
    GeometryDefinition,
)
from kernel.contracts.geometry_definition_set import (
    GeometryDefinitionSet,
)
from kernel.contracts.geometry_operation_type import (
    GeometryOperationType,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
)
from kernel.contracts.contour_definition import (
    ContourDefinition,
)


def main() -> None:
    contour = ContourDefinition(
        points=(
            (
                0.0,
                0.0,
            ),
            (
                20.0,
                0.0,
            ),
            (
                20.0,
                10.0,
            ),
            (
                0.0,
                10.0,
            ),
        ),
        closed=True,
        source="geometry_request_test",
    )

    geometry = GeometryDefinitionSet(
        definitions=(
            GeometryDefinition(
                outer_contour=contour,
                source="geometry_request_test",
            ),
        ),
        source="geometry_request_test",
    )

    request = GeometryRequest(
        geometry=geometry,
        operation=(
            GeometryOperationType.EXTRUDE
        ),
        output_id="extruded_body",
        parameters={
            "distance": 25.0,
            "direction": (
                0.0,
                0.0,
                5.0,
            ),
            "symmetric": True,
            "draft_angle": 2.0,
        },
        metadata={
            "test": True,
        },
    )

    request.validate()

    print()
    print("DOBO Geometry Request")
    print("---------------------")
    print(
        "Operation:",
        request.operation.value,
    )
    print(
        "Output:",
        request.output_id,
    )
    print(
        "Geometry definitions:",
        request.geometry_count,
    )
    print(
        "Distance:",
        request.get_parameter(
            "distance"
        ),
    )
    print(
        "Direction:",
        request.get_parameter(
            "direction"
        ),
    )
    print(
        "Symmetric:",
        request.get_parameter(
            "symmetric"
        ),
    )
    print(
        "Draft:",
        request.get_parameter(
            "draft_angle"
        ),
    )
    print(
        "Is extrude:",
        request.is_extrude,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()