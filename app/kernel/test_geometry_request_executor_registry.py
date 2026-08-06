"""
DOBO CAD Kernel

Geometry Request Executor Registry Test
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
from kernel.geometry import (
    ExtrudeRequestExecutor,
    GeometryRequestExecutorRegistry,
)


def circle(
    cx: float,
    cy: float,
    r: float,
    n: int = 64,
) -> tuple[tuple[float, float], ...]:

    return tuple(
        (
            cx + r * math.cos(
                -2 * math.pi * i / n
            ),
            cy + r * math.sin(
                -2 * math.pi * i / n
            ),
        )
        for i in range(n)
    )


def build_request() -> GeometryRequest:

    outer = ContourDefinition(
        id="outer",
        points=(
            (0.0, 0.0),
            (40.0, 0.0),
            (40.0, 30.0),
            (0.0, 30.0),
        ),
        closed=True,
        source="registry_test",
    )

    hole = ContourDefinition(
        id="hole",
        points=circle(
            20,
            15,
            5,
        ),
        closed=True,
        source="registry_test",
    )

    definition = GeometryDefinition(
        id="plate",
        outer_contour=outer,
        inner_contours=(hole,),
        source="registry_test",
    )

    geometry = GeometryDefinitionSet(
        id="geometry",
        definitions=(definition,),
        source="registry_test",
    )

    return GeometryRequest(
        id="extrude",
        geometry=geometry,
        operation=GeometryOperationType.EXTRUDE,
        parameters={
            "distance": 20.0,
            "direction": (
                0,
                0,
                1,
            ),
            "symmetric": True,
            "draft_angle": 0.0,
        },
        output_id="body",
    )


def main():

    registry = GeometryRequestExecutorRegistry()

    extrude = ExtrudeRequestExecutor()

    registry.register(
        extrude
    )

    registry.validate()

    assert registry.count == 1

    assert registry.contains(
        GeometryOperationType.EXTRUDE
    )

    assert (
        registry.get(
            GeometryOperationType.EXTRUDE
        )
        is extrude
    )

    request = build_request()

    result = registry.execute(
        request
    )

    result.validate()

    try:

        registry.register(
            ExtrudeRequestExecutor()
        )

        raise RuntimeError(
            "Duplicate registration "
            "should fail."
        )

    except ValueError:
        pass

    print()

    print(
        "DOBO Geometry Request Registry"
    )

    print(
        "------------------------------"
    )

    print(
        "Registered:",
        registry.count,
    )

    print(
        "Operations:",
        tuple(
            op.value
            for op
            in registry.operations
        ),
    )

    print(
        "Resolved:",
        result.request.operation.value,
    )

    print(
        "Volume:",
        result.solid.volume,
    )

    print(
        "Valid:",
        result.solid.is_valid,
    )

    print(
        "Valid: OK"
    )

    print()


if __name__ == "__main__":
    main()