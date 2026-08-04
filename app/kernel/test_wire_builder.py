import os
from typing import Any, cast

import cadquery as cq

from kernel.contracts.placement import Placement
from kernel.contracts.provider_request import (
    ProviderRequest,
)
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.circle_definition_provider import (
    CircleDefinitionProvider,
)
from kernel.services.geometry_projection_engine import (
    GeometryProjectionEngine,
)
from kernel.services.wire_builder import (
    WireBuilder,
)


def main() -> None:
    definitions = (
        CircleDefinitionProvider().execute(
            ProviderRequest(
                provider="circle_definition",
                parameters={
                    "radius": 10.0,
                    "samples": 64,
                },
            )
        )
    )

    projected = GeometryProjectionEngine().project(
        contours=definitions,
        placement=Placement(
            position=(
                0.0,
                0.0,
                40.0,
            ),
            angle_degrees=0.0,
        ),
        surface=Surface(
            type=SurfaceType.CYLINDER,
            parameters={
                "radius": 35.0,
                "height": 80.0,
                "origin": (
                    0.0,
                    0.0,
                    0.0,
                ),
            },
        ),
    )

    result = WireBuilder().build(
        projected
    )

    wire = result.wires[0]

    typed_wire = cast(
        Any,
        wire,
    )

    output_directory = os.path.join(
        "outputs",
        "kernel",
        "diagnostics",
    )

    os.makedirs(
        output_directory,
        exist_ok=True,
    )

    output_path = os.path.join(
        output_directory,
        "wire_builder_cylinder.step",
    )

    cq.exporters.export(
        wire,
        output_path,
    )

    print()
    print("DOBO Wire Builder")
    print("-----------------")
    print(
        "Wires:",
        result.count,
    )
    print(
        "Valid:",
        wire.isValid(),
    )
    print(
        "Closed:",
        typed_wire.IsClosed(),
    )
    print(
        "Edges:",
        len(
            wire.Edges()
        ),
    )
    print(
        "Vertices:",
        len(
            wire.Vertices()
        ),
    )
    print(
        "STEP:",
        output_path,
    )
    print()


if __name__ == "__main__":
    main()