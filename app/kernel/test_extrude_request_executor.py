"""
DOBO CAD Kernel

Extrude Request Executor Test

Validates planar extrusion with one real inner hole
through the specialized ExtrudeRequestExecutor.
"""

from __future__ import annotations

import math

from kernel.contracts.contour_definition import (
    ContourDefinition,
)
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
from kernel.geometry.extrude_request_executor import (
    ExtrudeRequestExecutor,
)


def build_circle_points(
    *,
    center_x: float,
    center_y: float,
    radius: float,
    samples: int,
) -> tuple[
    tuple[float, float],
    ...,
]:
    """
    Builds clockwise circle points for an inner hole.
    """

    return tuple(
        (
            center_x
            + radius
            * math.cos(
                -2.0
                * math.pi
                * index
                / samples
            ),
            center_y
            + radius
            * math.sin(
                -2.0
                * math.pi
                * index
                / samples
            ),
        )
        for index in range(
            samples
        )
    )


def main() -> None:
    width = 40.0
    height = 30.0
    hole_radius = 5.0
    extrusion_distance = 20.0
    circle_samples = 128

    outer_contour = ContourDefinition(
        id="outer_rectangle",
        points=(
            (
                0.0,
                0.0,
            ),
            (
                width,
                0.0,
            ),
            (
                width,
                height,
            ),
            (
                0.0,
                height,
            ),
        ),
        closed=True,
        source=(
            "extrude_request_executor_test"
        ),
        metadata={
            "role": "outer",
        },
    )

    inner_contour = ContourDefinition(
        id="inner_circle",
        points=build_circle_points(
            center_x=20.0,
            center_y=15.0,
            radius=hole_radius,
            samples=circle_samples,
        ),
        closed=True,
        source=(
            "extrude_request_executor_test"
        ),
        metadata={
            "role": "inner",
            "samples": circle_samples,
        },
    )

    definition = GeometryDefinition(
        id="plate_with_hole",
        outer_contour=outer_contour,
        inner_contours=(
            inner_contour,
        ),
        source=(
            "extrude_request_executor_test"
        ),
    )

    geometry = GeometryDefinitionSet(
        id="plate_geometry",
        definitions=(
            definition,
        ),
        source=(
            "extrude_request_executor_test"
        ),
    )

    request = GeometryRequest(
        id="plate_extrusion_request",
        geometry=geometry,
        operation=(
            GeometryOperationType.EXTRUDE
        ),
        parameters={
            "distance": (
                extrusion_distance
            ),
            "direction": (
                0.0,
                0.0,
                1.0,
            ),
            "symmetric": True,
            "draft_angle": 0.0,
        },
        output_id="plate_body",
        metadata={
            "test": True,
        },
    )

    executor = ExtrudeRequestExecutor()

    if not executor.supports(
        GeometryOperationType.EXTRUDE
    ):
        raise RuntimeError(
            "Executor must support EXTRUDE."
        )

    result = executor.execute(
        request
    )

    result.validate()

    solid = result.solid

    polygonal_hole_area = (
        circle_samples
        * hole_radius
        * hole_radius
        * math.sin(
            2.0
            * math.pi
            / circle_samples
        )
        / 2.0
    )

    expected_volume = (
        (
            width
            * height
            - polygonal_hole_area
        )
        * extrusion_distance
    )

    if solid.volume is None:
        raise RuntimeError(
            "Expected Solid volume."
        )

    if not math.isclose(
        solid.volume,
        expected_volume,
        rel_tol=1e-6,
        abs_tol=1e-6,
    ):
        raise RuntimeError(
            "Unexpected extrusion volume: "
            f"{solid.volume}."
        )

    if solid.bounding_box is None:
        raise RuntimeError(
            "Expected Solid bounding box."
        )

    expected_minimum = (
        0.0,
        0.0,
        -10.0,
    )

    expected_maximum = (
        40.0,
        30.0,
        10.0,
    )

    for actual, expected in zip(
        solid.bounding_box.minimum,
        expected_minimum,
    ):
        if not math.isclose(
            actual,
            expected,
            abs_tol=1e-7,
        ):
            raise RuntimeError(
                "Unexpected minimum bounding box."
            )

    for actual, expected in zip(
        solid.bounding_box.maximum,
        expected_maximum,
    ):
        if not math.isclose(
            actual,
            expected,
            abs_tol=1e-7,
        ):
            raise RuntimeError(
                "Unexpected maximum bounding box."
            )

    if not solid.is_valid:
        raise RuntimeError(
            "Expected valid Solid."
        )

    if result.geometry_count != 1:
        raise RuntimeError(
            "Expected one generated geometry."
        )

    print()
    print("DOBO Extrude Request Executor")
    print("-----------------------------")
    print(
        "Operation:",
        request.operation.value,
    )
    print(
        "Geometry definitions:",
        request.geometry.count,
    )
    print(
        "Contours:",
        definition.contour_count,
    )
    print(
        "Holes:",
        definition.hole_count,
    )
    print(
        "Generated geometry:",
        result.geometry_count,
    )
    print(
        "Solid volume:",
        solid.volume,
    )
    print(
        "Center:",
        solid.center_of_mass,
    )
    print(
        "Bounds:",
        (
            solid.bounding_box.minimum,
            solid.bounding_box.maximum,
        ),
    )
    print(
        "Valid:",
        solid.is_valid,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()